from playwright.sync_api import sync_playwright
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import os
import argparse
import time
import pandas as pd
import sqlite3
from datetime import datetime
from dateutil import parser as date_parser

# ---- CLI support added
def cli_parse_args():
    parser = argparse.ArgumentParser(description='Scrape NTU scholarship list and detail pages')
    parser.add_argument('--output-file', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'data', 'scholarships.csv'), help='CSV output file')
    parser.add_argument('--db-file', type=str, default=os.path.join(os.path.dirname(__file__), '..', 'data', 'scholarships.db'), help='SQLite database file')
    parser.add_argument('--headless', dest='headless', action='store_true', help='Run headless browser')
    parser.add_argument('--no-headless', dest='headless', action='store_false', help='Run with browser visible')
    parser.set_defaults(headless=True)
    parser.add_argument('--timeout', type=int, default=30000, help='page.goto timeout in ms')
    parser.add_argument('--retry', type=int, default=2, help='Retry attempts for page.goto')
    parser.add_argument('--start-page', type=int, default=1, help='Start from page number (for resume)')
    parser.add_argument('--max-pages', type=int, default=30, help='Maximum pages to scrape')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds')
    return parser.parse_args()

args = cli_parse_args()

list_base_url = "https://advisory.ntu.edu.tw/CMS/Scholarship?pageId=232&keyword=&applicant_type=&sort=f_apply_end_date&pageIndex={}&show_way=all"
detail_base_url = "https://advisory.ntu.edu.tw/CMS/ScholarshipDetail?id="


def parse_date_range(date_text):
    """
    解析申請日期文字，提取開始日期和截止日期
    例如：「自2025/12/3起至2026/2/5止。」-> (2025-12-03, 2026-02-05)
    """
    if not date_text or not isinstance(date_text, str):
        return None, None
    
    try:
        # 尋找日期格式：YYYY/MM/DD 或 YYYY-MM-DD
        date_pattern = re.findall(r'\d{2,4}[/-]\d{1,2}[/-]\d{1,2}', date_text)
        
        if len(date_pattern) >= 2:
            # 找到至少兩個日期，第一個是開始日期，最後一個是截止日期
            start_date = date_parser.parse(date_pattern[0], fuzzy=True).date()
            end_date = date_parser.parse(date_pattern[-1], fuzzy=True).date()
            return str(start_date), str(end_date)
        elif len(date_pattern) == 1:
            # 只有一個日期，可能是截止日期
            date = date_parser.parse(date_pattern[0], fuzzy=True).date()
            return None, str(date)
    except Exception as e:
        print(f"  警告：日期解析失敗 '{date_text}': {e}")
    
    return None, None


def extract_scholarship_ids_from_list_page(html):
    """從列表頁面提取獎學金 ID"""
    soup = BeautifulSoup(html, 'lxml')
    ids = []
    
    # 方法1：從 <tr class="tr_data" id="獎學金ID"> 提取
    for tr in soup.find_all('tr', class_='tr_data'):
        scholarship_id = tr.get('id')
        if scholarship_id and scholarship_id.isdigit():
            if scholarship_id not in ids:
                ids.append(scholarship_id)
    
    # 方法2：備用方案 - 從連結提取（如果有的話）
    if not ids:
        for a in soup.find_all('a', href=True):
            href = a['href']
            match = re.search(r'ScholarshipDetail\?id=(\d+)', href)
            if match:
                scholarship_id = match.group(1)
                if scholarship_id not in ids:
                    ids.append(scholarship_id)
    
    return ids

def extract_fields(html, base_page_url=None):
    """
    Extract fields from the detail table.
    Now also extracts attachment links properly.
    """
    soup = BeautifulSoup(html, 'lxml')
    table = soup.find('table', class_='blank-line-half')
    fields = {}
    
    if table:
        for tr in table.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) >= 2:
                key = tds[0].get_text(strip=True)
                
                # 特別處理附加檔案欄位
                if any(keyword in key for keyword in ['附加檔案', '附件', '附檔', '相關檔']):
                    # 提取所有連結
                    links = []
                    for a in tds[1].find_all('a', href=True):
                        href = a['href'].strip()
                        # 轉換相對路徑為絕對路徑
                        if base_page_url:
                            href = urljoin(base_page_url, href)
                        link_text = a.get_text(strip=True)
                        # 格式：連結文字 [URL]
                        links.append(f"{link_text} [{href}]")
                    
                    # 也尋找純文字中的 URL
                    text_content = tds[1].get_text(' ')
                    for url_match in re.findall(r'https?://[^\s)"\']+', text_content):
                        if not any(url_match in link for link in links):
                            links.append(url_match)
                    
                    fields[key] = " | ".join(links) if links else tds[1].get_text(" ", strip=True)
                else:
                    # 一般欄位
                    value = tds[1].get_text(" ", strip=True)
                    fields[key] = value
                    
    return fields

def extract_attachment_links(html, base_page_url=None):
    """Extract links from the table row whose label contains 附加檔案/附件/附檔等 keywords."""
    soup = BeautifulSoup(html, 'lxml')
    table = soup.find('table', class_='blank-line-half')
    links = []
    if not table:
        return links
    for tr in table.find_all('tr'):
        tds = tr.find_all('td')
        if len(tds) >= 2:
            key = tds[0].get_text(strip=True)
            if any(k in key for k in ['附加檔案', '附件', '附檔', '相關檔']):
                for a in tds[1].find_all('a', href=True):
                    href = a['href'].strip()
                    if base_page_url:
                        href = urljoin(base_page_url, href)
                    links.append(href)
                # also look for plain text urls inside the td
                for txt in re.findall(r'https?://[^\s)"\']+', tds[1].get_text(' ')):
                    if txt not in links:
                        links.append(txt)
                break
    return links

out_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(out_dir, exist_ok=True)
csv_file = args.output_file
db_file = args.db_file

# 定義 CSV 表頭
headers = ['ID', 'URL', '類別名稱', '開始日期', '截止日期', '獎學金名稱', '申請地點',
           '附加檔案', '獎學金金額', '獎學金名額', '申請對象',
           '申請資格', '繳交文件', '爬取頁數', '爬取時間']

def init_database(db_path):
    """初始化 SQLite 資料庫"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 建立獎學金資料表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scholarships (
            id TEXT PRIMARY KEY,
            url TEXT,
            category TEXT,
            start_date TEXT,
            end_date TEXT,
            scholarship_name TEXT,
            location TEXT,
            attachments TEXT,
            amount TEXT,
            quota TEXT,
            target_audience TEXT,
            qualifications TEXT,
            required_documents TEXT,
            page_number INTEGER,
            scraped_time TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"✓ 資料庫初始化完成: {db_path}")

def save_to_database(db_path, data_rows):
    """將資料寫入 SQLite 資料庫"""
    if not data_rows:
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for row in data_rows:
        # 使用 INSERT OR REPLACE 來處理重複資料
        cursor.execute('''
            INSERT OR REPLACE INTO scholarships 
            (id, url, category, start_date, end_date, scholarship_name, 
             location, attachments, amount, quota, target_audience, qualifications, 
             required_documents, page_number, scraped_time, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', row)
    
    conn.commit()
    conn.close()
    print(f"✓ 已寫入 {len(data_rows)} 筆資料到資料庫")

def load_existing_data(csv_path):
    """載入已存在的資料，返回已爬取的 ID 集合"""
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path, encoding='utf-8-sig')
            existing_ids = set(df['ID'].astype(str).tolist())
            print(f"發現已存在資料：{len(existing_ids)} 筆")
            return existing_ids
        except Exception as e:
            print(f"讀取現有資料失敗：{e}")
            return set()
    return set()

def save_page_data(csv_path, data_rows, mode='a'):
    """將單頁資料寫入 CSV"""
    file_exists = os.path.exists(csv_path)
    
    with open(csv_path, mode, newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        
        # 如果是新檔案或覆寫模式，寫入表頭
        if mode == 'w' or not file_exists:
            writer.writerow(headers)
        
        # 寫入資料
        writer.writerows(data_rows)
    
    print(f"✓ 已寫入 {len(data_rows)} 筆資料到 {csv_path}")

def scrape_detail_page(page, scholarship_id, page_number, timeout, retry_count, delay):
    """爬取單個獎學金詳細頁面"""
    url = detail_base_url + str(scholarship_id)
    print(f"  抓取 ID={scholarship_id}...", end=' ')
    
    for attempt in range(max(1, retry_count)):
        try:
            page.goto(url, timeout=timeout)
            page.wait_for_selector("body")
            time.sleep(delay)  # 禮貌性延遲
            
            content = page.content()
            fields = extract_fields(content, base_page_url=url)
            attach_links = extract_attachment_links(content, base_page_url=url)
            
            # 使用 extract_fields 的結果，如果為空才用 extract_attachment_links
            attach_field = fields.get('附加檔案', '')
            if not attach_field or (isinstance(attach_field, str) and attach_field.strip() == ''):
                attach_field = ", ".join(attach_links) if attach_links else ''
            
            # 解析申請日期
            application_date_text = fields.get('申請日期', '')
            start_date, end_date = parse_date_range(application_date_text)
            
            # 構建資料列
            row = [
                scholarship_id,
                url,
                fields.get('類別名稱', ''),
                start_date or '',
                end_date or '',
                fields.get('獎學金名稱', ''),
                fields.get('申請地點', ''),
                attach_field,
                fields.get('獎學金金額', ''),
                fields.get('獎學金名額', ''),
                fields.get('申請對象', ''),
                fields.get('申請資格', ''),
                fields.get('繳交文件', ''),
                page_number,
                time.strftime('%Y-%m-%d %H:%M:%S')
            ]
            
            print("✓")
            return row
            
        except Exception as e:
            if attempt < retry_count - 1:
                print(f"失敗 (嘗試 {attempt+1}/{retry_count})，重試中...", end=' ')
                time.sleep(2)
            else:
                print(f"✗ 失敗: {str(e)[:50]}")
                # 返回錯誤列
                return [
                    scholarship_id,
                    url,
                    f'抓取失敗: {str(e)[:100]}',
                    '', '', '', '', '', '', '', '', '',
                    page_number,
                    time.strftime('%Y-%m-%d %H:%M:%S')
                ]
    
    return None

print("=" * 60)
print("台大獎學金爬蟲")
print("=" * 60)
print(f"CSV 輸出: {csv_file}")
print(f"資料庫輸出: {db_file}")
print(f"開始頁數: {args.start_page}")
print(f"最大頁數: {args.max_pages}")
print(f"每頁延遲: {args.delay} 秒")
print(f"請求逾時: {args.timeout} ms")
print(f"重試次數: {args.retry}")
print("=" * 60)

# 初始化資料庫
init_database(db_file)

# 載入已存在的資料
existing_ids = load_existing_data(csv_file)

# 如果從第一頁開始且沒有現有資料，初始化檔案
if args.start_page == 1 and not existing_ids:
    save_page_data(csv_file, [], mode='w')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=args.headless)
    page = browser.new_page()
    
    total_scraped = 0
    total_skipped = 0
    
    try:
        for page_num in range(args.start_page, args.start_page + args.max_pages):
            list_url = list_base_url.format(page_num)
            print(f"\n第 {page_num} 頁 - {list_url}")
            
            try:
                page.goto(list_url, timeout=args.timeout)
                page.wait_for_selector("body")
                time.sleep(args.delay)
                
                # 提取該頁所有獎學金 ID
                content = page.content()
                scholarship_ids = extract_scholarship_ids_from_list_page(content)
                
                if not scholarship_ids:
                    print(f"⚠ 第 {page_num} 頁沒有找到獎學金，可能已到最後一頁")
                    break
                
                print(f"發現 {len(scholarship_ids)} 個獎學金ID")
                
                # 爬取該頁每個獎學金的詳細資料
                page_data = []
                for idx in scholarship_ids:
                    # 檢查是否已爬取過
                    if str(idx) in existing_ids:
                        print(f"  ID={idx} 已存在，跳過")
                        total_skipped += 1
                        continue
                    
                    row = scrape_detail_page(page, idx, page_num, args.timeout, args.retry, args.delay)
                    if row:
                        page_data.append(row)
                        existing_ids.add(str(idx))
                        total_scraped += 1
                
                # 每頁爬完立即寫入檔案
                if page_data:
                    save_page_data(csv_file, page_data, mode='a')
                    save_to_database(db_file, page_data)
                else:
                    print("  本頁沒有新資料需要寫入")
                
                print(f"第 {page_num} 頁完成 (新增 {len(page_data)} 筆，跳過 {len(scholarship_ids) - len(page_data)} 筆)")
                
            except Exception as e:
                print(f"✗ 第 {page_num} 頁處理失敗: {e}")
                print("將繼續下一頁...")
                continue
    
    finally:
        browser.close()
        
        print("\n" + "=" * 60)
        print("爬取完成！")
        print("=" * 60)
        print(f"總共爬取: {total_scraped} 筆")
        print(f"跳過已存在: {total_skipped} 筆")
        print(f"CSV 檔案: {csv_file}")
        print(f"資料庫: {db_file}")
        print("=" * 60)


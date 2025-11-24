"""
驗證獎學金附件下載結果的腳本

此腳本將：
1. 計算應下載的連結總數 (N_link) 根據原始資料文件
2. 分析下載日誌文件以計算實際成功與失敗的下載數量
3. 輸出詳細的下載失敗清單以供進一步調查 
"""


import pandas as pd
import re
import os
from pathlib import Path

# --- Configuration ---
# 假設您的原始資料文件
SCHOLARSHIPS_FILE = Path("data/raw/scholarships.csv")
# 附加檔案欄位名稱
ATTACHMENT_COL = '附加檔案'
# 日誌文件路徑
LOG_FILE = Path("download_log.txt")
# 下載資料夾路徑
ATTACHMENTS_DIR = Path("data/raw/attachments")
# ---------------------

# Regex to match URLs in the attachment column (to calculate N_link)
URL_REGEX = r'https?://[^\s\]]+'

# Regex to extract status from the log file
# Matches: Successfully downloaded {url} OR Failed to download {url}
SUCCESS_LOG_REGEX = r'Successfully downloaded (https?://.*?) to'
FAILURE_LOG_REGEX = r'Failed to download (https?://.*?) for scholarship (\w+?): (.*)'

def calculate_n_link(csv_path: Path, attachment_col: str) -> dict:
    """
    計算應下載的連結總數 (N_link) 並建立連結清單
    回傳: {url: scholarship_id}
    """
    link_map = {}
    
    try:
        # 假設 CSV 文件是以 UTF-8 編碼儲存 (爬蟲腳本的常見輸出)
        df = pd.read_csv(csv_path, encoding='utf-8')
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {csv_path}")
        return {}
    except UnicodeDecodeError:
        print(f"錯誤：CSV 檔案 {csv_path} 編碼錯誤，嘗試使用 Big5 讀取...")
        try:
            df = pd.read_csv(csv_path, encoding='big5')
        except Exception as e:
            print(f"二次嘗試失敗：{e}")
            return {}


    for index, row in df.iterrows():
        scholarship_id = row.get('ID', index)
        attachment_text = row.get(attachment_col)
        
        if pd.isna(attachment_text) or not attachment_text:
            continue
            
        # 尋找所有 URL
        links = re.findall(URL_REGEX, str(attachment_text))
        
        for url in links:
            # 使用 URL 作為鍵，確保每個連結只計算一次
            link_map[url] = scholarship_id
            
    return link_map

def analyze_log_file(log_path: Path) -> dict:
    """
    分析日誌文件，計算成功、失敗的下載，並記錄失敗詳情
    回傳: {
        'successful_urls': set,
        'failed_details': [(scholarship_id, url, reason), ...],
        'processed_urls_in_log': set
    }
    """
    successful_urls = set()
    failed_details = []
    processed_urls = set()

    try:
        # **** 修復點：明確指定編碼為 utf-8，並忽略無法解碼的字元 ****
        # 這是處理 'UnicodeDecodeError' 的標準做法
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                # 檢查成功下載
                success_match = re.search(SUCCESS_LOG_REGEX, line)
                if success_match:
                    url = success_match.group(1).strip()
                    successful_urls.add(url)
                    processed_urls.add(url)
                    continue

                # 檢查下載失敗
                failure_match = re.search(FAILURE_LOG_REGEX, line)
                if failure_match:
                    url = failure_match.group(1).strip()
                    sch_id = failure_match.group(2).strip()
                    reason = failure_match.group(3).strip()
                    failed_details.append((sch_id, url, reason))
                    processed_urls.add(url)
                    continue

    except FileNotFoundError:
        print(f"警告：找不到日誌檔案 {log_path}，無法進行詳細審核。")
        return None

    return {
        'successful_urls': successful_urls,
        'failed_details': failed_details,
        'processed_urls_in_log': processed_urls
    }

def main_verification():
    """執行下載驗證主程序"""
    
    # 1. 計算應下載連結總數 (N_link)
    all_links = calculate_n_link(SCHOLARSHIPS_FILE, ATTACHMENT_COL)
    N_link = len(all_links)
    
    if N_link == 0:
        print("無法計算應下載連結總數，請確認 CSV 路徑及欄位是否正確。")
        return

    # 2. 分析日誌文件
    log_analysis = analyze_log_file(LOG_FILE)
    
    if not log_analysis:
        print(f"應下載連結總數 (N_link): {N_link}")
        print(f"--- 結束驗證 ---")
        return
        
    N_success = len(log_analysis['successful_urls'])
    N_fail = len(log_analysis['failed_details'])
    N_processed_log = len(log_analysis['processed_urls_in_log'])
    
    # 3. 找出遺漏的連結 (Missing URLs)
    # 理論上，N_link 應該等於 N_processed_log (成功 + 失敗，且不重複)
    all_links_set = set(all_links.keys())
    
    # 未出現在日誌中的連結 (可能是爬蟲邏輯錯誤或資料問題，但下載腳本沒有嘗試處理)
    unprocessed_urls = all_links_set - log_analysis['processed_urls_in_log']
    
    # 4. 產生最終報告
    
    print("\n" + "="*80)
    print("                🏆 獎學金附件下載驗證報告 (QUANTITATIVE) 🏆")
    print("="*80)
    print(f"  [1] 應處理連結總數 (N_link, 根據 CSV): {N_link}")
    print(f"  [2] 日誌記錄的下載嘗試總數:        {N_processed_log}")
    print("-" * 80)
    
    if N_link != N_processed_log:
        print(f"  ⚠️ 警告: 連結數與日誌記錄數不符 ({N_link} vs {N_processed_log})。請檢查爬蟲邏輯。")
        
    print(f"  ✅ 實際下載成功數量:               {N_success}")
    print(f"  ❌ 實際下載失敗數量 (日誌記錄):      {N_fail}")
    
    # 5. 輸出失敗詳情 (QUALITATIVE)
    if N_fail > 0:
        print("\n" + "="*30 + " ❌ 詳細下載失敗清單 " + "="*30)
        for sch_id, url, reason in log_analysis['failed_details']:
            print(f"  [ID: {sch_id}] URL: {url[:60]}... 失敗原因: {reason}")
        
    # 6. 輸出遺漏清單
    if unprocessed_urls:
        print("\n" + "="*30 + " ⚠️ 未處理連結清單 (UNPROCESSED) " + "="*20)
        for url in unprocessed_urls:
             print(f"  [ID: {all_links[url]}] URL: {url[:60]}...")
             
    print("\n" + "="*80)
    print("下一步建議: 如果失敗數量可接受，請開始進行文件解析 (文字擷取)。")
    print("="*80)
    
    # 額外檢查檔案數量
    if ATTACHMENTS_DIR.exists():
        N_disk_file = sum(1 for item in ATTACHMENTS_DIR.iterdir() if item.is_file())
        print(f"\n (磁碟檔案數檢查: {N_disk_file} 個檔案存於 {ATTACHMENTS_DIR.name}/)")
    else:
        print(f"\n (磁碟檔案數檢查: 找不到資料夾 {ATTACHMENTS_DIR.name}/)")


if __name__ == "__main__":
    main_verification()
"""
簡單的資料庫查詢工具
用於測試和檢查 SQLite 資料庫內容
"""

import sqlite3
import pandas as pd
import os
import argparse

def connect_db(db_path):
    """連接資料庫"""
    if not os.path.exists(db_path):
        print(f"資料庫不存在: {db_path}")
        return None
    return sqlite3.connect(db_path)

def get_stats(conn):
    """取得資料庫統計資訊"""
    cursor = conn.cursor()
    
    # 總筆數
    cursor.execute("SELECT COUNT(*) FROM scholarships")
    total = cursor.fetchone()[0]
    
    # 類別統計
    cursor.execute("SELECT category, COUNT(*) FROM scholarships GROUP BY category ORDER BY COUNT(*) DESC")
    categories = cursor.fetchall()
    
    # 最近更新
    cursor.execute("SELECT id, scholarship_name, scraped_time FROM scholarships ORDER BY scraped_time DESC LIMIT 5")
    recent = cursor.fetchall()
    
    print("\n" + "=" * 60)
    print("資料庫統計")
    print("=" * 60)
    print(f"總筆數: {total}")
    
    print(f"\n類別分布:")
    for cat, count in categories[:10]:
        print(f"  {cat or '(未分類)'}: {count} 筆")
    
    print(f"\n最近更新（前5筆）:")
    for id, name, time in recent:
        print(f"  [{id}] {name[:30]}... ({time})")
    print("=" * 60)

def search_scholarships(conn, keyword=None, category=None, target=None, limit=10):
    """搜尋獎學金"""
    query = "SELECT id, scholarship_name, category, target_audience, amount FROM scholarships WHERE 1=1"
    params = []
    
    if keyword:
        query += " AND (scholarship_name LIKE ? OR qualifications LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    
    if category:
        query += " AND category LIKE ?"
        params.append(f"%{category}%")
    
    if target:
        query += " AND target_audience LIKE ?"
        params.append(f"%{target}%")
    
    query += f" LIMIT {limit}"
    
    df = pd.read_sql_query(query, conn, params=params)
    return df

def export_to_csv(conn, output_path):
    """匯出全部資料到 CSV"""
    df = pd.read_sql_query("SELECT * FROM scholarships ORDER BY id", conn)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"✓ 已匯出 {len(df)} 筆資料到 {output_path}")

def main():
    parser = argparse.ArgumentParser(description='查詢獎學金資料庫')
    parser.add_argument('--db', type=str, default='data/scholarships.db', help='資料庫路徑')
    parser.add_argument('--stats', action='store_true', help='顯示統計資訊')
    parser.add_argument('--search', type=str, help='搜尋關鍵字')
    parser.add_argument('--category', type=str, help='篩選類別')
    parser.add_argument('--target', type=str, help='篩選申請對象')
    parser.add_argument('--export', type=str, help='匯出到 CSV 檔案')
    parser.add_argument('--limit', type=int, default=10, help='搜尋結果數量限制')
    
    args = parser.parse_args()
    
    # 連接資料庫
    conn = connect_db(args.db)
    if not conn:
        return
    
    try:
        if args.stats:
            get_stats(conn)
        
        if args.search or args.category or args.target:
            print(f"\n搜尋條件: 關鍵字={args.search}, 類別={args.category}, 對象={args.target}")
            results = search_scholarships(conn, args.search, args.category, args.target, args.limit)
            print(f"\n找到 {len(results)} 筆結果:\n")
            print(results.to_string())
        
        if args.export:
            export_to_csv(conn, args.export)
        
        # 如果沒有任何參數，顯示統計
        if not any([args.stats, args.search, args.category, args.target, args.export]):
            get_stats(conn)
    
    finally:
        conn.close()

if __name__ == '__main__':
    main()

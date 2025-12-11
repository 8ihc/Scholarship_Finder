import os
import json

# 測試腳本：合併單筆 result_ID.json 與原始獎學金元數據

# 設定路徑
SOURCE_FILE = os.path.join("data", "processed", "scholarships_with_full_text_for_llm.json")
TAGS_DIR = os.path.join("data", "analysis")
OUTPUT_DIR = os.path.join("data", "merged")

# 要保留的欄位
METADATA_FIELDS = [
    "id", "url", "category", "start_date", "end_date", 
    "scholarship_name", "application_location", "attachments",
    "amount", "quota", "eligibility", "required_documents", "scraped_at"
]

def merge_single_scholarship(scholarship_id):
    """
    測試：合併單筆獎學金的標籤結果與元數據
    
    Args:
        scholarship_id: 獎學金 ID (例如 7897)
    
    Returns:
        合併後的字典
    """
    # 1. 讀取原始獎學金資料
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        all_scholarships = json.load(f)
    
    # 2. 找到對應的獎學金
    scholarship_data = None
    for item in all_scholarships:
        if item.get('id') == scholarship_id:
            scholarship_data = item
            break
    
    if not scholarship_data:
        print(f"❌ 找不到 ID {scholarship_id} 的獎學金資料")
        return None
    
    # 3. 讀取標籤結果
    tags_file = os.path.join(TAGS_DIR, f"result_{scholarship_id}.json")
    if not os.path.exists(tags_file):
        print(f"❌ 找不到標籤檔案: {tags_file}")
        return None
    
    with open(tags_file, 'r', encoding='utf-8') as f:
        tags_data = json.load(f)
    
    # 4. 提取需要的元數據欄位
    metadata = {}
    for field in METADATA_FIELDS:
        if field in scholarship_data:
            metadata[field] = scholarship_data[field]
    
    # 5. 合併：元數據 + 標籤結構
    merged_data = {
        **metadata,  # 先放元數據
        "tags": {
            "groups": tags_data.get("groups", []),
            "common_tags": tags_data.get("common_tags", [])
        }
    }
    
    return merged_data

def batch_merge_scholarships(limit=30):
    """
    批次合併多筆獎學金，輸出為單一 JSON 陣列
    
    Args:
        limit: 要處理的數量（預設 30 筆）
    """
    print(f"--- 開始批次合併（前 {limit} 筆）---")
    
    # 1. 讀取所有獎學金資料
    with open(SOURCE_FILE, 'r', encoding='utf-8') as f:
        all_scholarships = json.load(f)
    
    # 2. 取得 analysis 資料夾中已處理的 ID
    processed_ids = []
    for filename in os.listdir(TAGS_DIR):
        if filename.startswith("result_") and filename.endswith(".json"):
            # 提取 ID（例如 result_7897.json -> 7897）
            scholarship_id = int(filename.replace("result_", "").replace(".json", ""))
            processed_ids.append(scholarship_id)
    
    processed_ids.sort()  # 排序
    processed_ids = processed_ids[:limit]  # 只取前 N 筆
    
    print(f"找到 {len(processed_ids)} 筆已處理的標籤資料")
    print(f"準備合併的 ID: {processed_ids[:10]}{'...' if len(processed_ids) > 10 else ''}")
    
    # 3. 批次合併到陣列
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    merged_list = []
    success_count = 0
    fail_count = 0
    
    for scholarship_id in processed_ids:
        result = merge_single_scholarship(scholarship_id)
        
        if result:
            merged_list.append(result)
            success_count += 1
            print(f"✅ [{success_count}/{len(processed_ids)}] ID {scholarship_id} 合併成功")
        else:
            fail_count += 1
            print(f"❌ ID {scholarship_id} 合併失敗")
    
    # 4. 輸出為單一 JSON 檔案
    output_file = os.path.join(OUTPUT_DIR, f"scholarships_merged_{limit}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_list, f, indent=4, ensure_ascii=False)
    
    print(f"\n--- 批次合併完成 ---")
    print(f"成功: {success_count}")
    print(f"失敗: {fail_count}")
    print(f"輸出檔案: {output_file}")
    print(f"總筆數: {len(merged_list)}")

def test_merge():
    """執行測試"""
    # 測試 ID（你可以改成任何已處理的 ID）
    test_id = 7897
    
    print(f"--- 測試合併 ID {test_id} ---")
    
    result = merge_single_scholarship(test_id)
    
    if result:
        # 輸出到測試檔案
        output_file = os.path.join(OUTPUT_DIR, f"merged_test_{test_id}.json")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        
        print(f"✅ 合併成功！")
        print(f"輸出檔案: {output_file}")
        print(f"\n欄位預覽:")
        print(f"  - 元數據欄位: {list(result.keys())[:9]}")
        print(f"  - 標籤組別數量: {len(result['tags']['groups'])}")
        print(f"  - 通用標籤數量: {len(result['tags']['common_tags'])}")
    else:
        print("❌ 合併失敗")

if __name__ == "__main__":
    # 執行批次合併（前 300 筆）
    batch_merge_scholarships(limit=300)
    
    # 如果只想測試單筆，註解上面那行，取消註解下面這行
    # test_merge()

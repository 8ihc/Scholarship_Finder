import json
import os

def process_and_analyze_text_length(merged_data_path, output_path):
    """
    為整合後的獎學金資料新增 'full_text_for_llm' 欄位（無截斷），
    並分析所有欄位的最大字元長度。

    Args:
        merged_data_path (str): 整合後的 JSON 檔案路徑 (包含 attachment_details)。
        output_path (str): 輸出包含新欄位的 JSON 檔案路徑。
    """
    
    print(f"--- 1. 載入 merged json file：{merged_data_path} ---")
    
    # 檢查輸入檔案是否存在
    if not os.path.exists(merged_data_path):
        print(f"錯誤：找不到輸入檔案 {merged_data_path}。請確認檔案路徑和名稱。")
        return

    try:
        with open(merged_data_path, 'r', encoding='utf-8') as f:
            integrated_data = json.load(f)
    except Exception as e:
        print(f"載入檔案時發生錯誤: {e}")
        return

    print(f"載入 {len(integrated_data)} 筆獎學金資料。")
    print(f"--- 2. 遍歷資料並創建 'full_text_for_llm' 欄位（無截斷） ---")
    
    # 用於追蹤最大長度和對應 ID
    max_length = 0
    max_length_id = None
    
    for scholarship in integrated_data:
        full_text_parts = []
        
        # --- 2.1 核心元數據區塊 ---
        metadata_block = [
            "### 獎學金核心元數據 (FOR LLM REFERENCE) ###",
            f"名稱: {scholarship.get('scholarship_name', 'N/A')}",
            f"ID: {scholarship.get('id', 'N/A')}",
            f"起始日期: {scholarship.get('start_date', 'N/A')}",
            f"截止日期: {scholarship.get('end_date', 'N/A')}",
            f"金額: {scholarship.get('amount', 'N/A')}",
            f"名額: {scholarship.get('quota', 'N/A')}",
            f"申請地點: {scholarship.get('application_location', 'N/A')}",
        ]
        full_text_parts.append('\n'.join(metadata_block))

        # --- 2.2 網站公告文本區塊 ---
        full_text_parts.append(
            f"\n### 網站公告：申請資格 (Eligibility) - 原始文本 ###\n"
            f"{scholarship.get('eligibility', '未提供網站申請資格。')}"
        )
        full_text_parts.append(
            f"\n### 網站公告：應繳文件 (Required Documents) - 原始文本 ###\n"
            f"{scholarship.get('required_documents', '未提供網站應繳文件。')}"
        )
        
        # --- 2.3 附件解析內容區塊 (無截斷處理) ---
        attachments = scholarship.get('attachment_details')
        if attachments:
            attachment_block = ["\n### 附件解析內容 ###"]
            
            for idx, attachment in enumerate(attachments):
                # *** 關鍵修改：直接使用完整的解析文本，不進行字元截斷 ***
                text = attachment.get('parsed_text', '解析文本為空。')
                
                attachment_block.append(
                    f"\n--- 附件 {idx + 1}: {attachment.get('name', '未命名附件')} ---"
                    f"\n{text}"
                )
            
            full_text_parts.append('\n'.join(attachment_block))
        else:
            full_text_parts.append("\n### 附件解析內容 ###\n無附件內容。")

        # --- 2.4 合併所有部分並記錄長度 ---
        scholarship['full_text_for_llm'] = '\n\n'.join(full_text_parts)
        current_length = len(scholarship['full_text_for_llm'])
        
        # 更新最大長度紀錄
        if current_length > max_length:
            max_length = current_length
            max_length_id = scholarship.get('id')
            
        # print(f"  > ID {scholarship.get('id')} 創建完成 (長度: {current_length} 字元).")


    print(f"\n--- 3. 寫入包含 'full_text_for_llm' 的新 JSON 檔案：{output_path} ---")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(integrated_data, f, ensure_ascii=False, indent=2)
        print(f"處理完成！結果已儲存至 {output_path}。")
    except Exception as e:
        print(f"寫入檔案時發生錯誤: {e}")
        
    print(f"\n=======================================================")
    print(f"🎉 字元長度分析結果 🎉")
    print(f"總共處理了 {len(integrated_data)} 筆獎學金。")
    print(f"最大 'full_text_for_llm' 字元長度為: **{max_length}**")
    print(f"該筆獎學金的 ID 是: **{max_length_id}**")
    print(f"=======================================================")


# --- 執行腳本 ---
# 請將這裡的 'your_merged_data.json' 替換為您實際整合好的檔案名
INPUT_JSON_PATH = 'scholarships_with_attachments.json' 
OUTPUT_JSON_PATH = 'scholarships_with_full_text_for_llm.json'

process_and_analyze_text_length(INPUT_JSON_PATH, OUTPUT_JSON_PATH)
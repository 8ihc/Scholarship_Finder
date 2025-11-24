"""
Cloud OCR 處理器
此腳本處理經 document_parsing and OCR staging.py 標記為 'OCR_REQUIRED' 的檔案。
它利用 Google Cloud Vision API 的非同步批次處理功能來處理 PDF 和圖像，
並將 OCR 結果回填到 scholarships_parsed_texts.json 中。
"""

import os
import re
import json
import time
import argparse
import logging
import unicodedata
from pathlib import Path
from google.cloud import storage, vision
from google.longrunning import operations_pb2
from google.api_core import operation as longrunning
from typing import List, Dict, Any

# --- Configuration (請根據您的環境設定) ---
# 服務帳戶金鑰檔案路徑
SERVICE_ACCOUNT_FILE = "C:\\Users\\8ihc8\\Desktop\\new_scholarship\\service-account-key.json.json"

# Google Cloud Storage Bucket 名稱 (必須預先創建)
GCS_BUCKET_NAME = "ntu-scholarship-ocr-taipei-2025" 
GCS_INPUT_FOLDER = "ocr_input/"
GCS_OUTPUT_FOLDER = "ocr_output/"

# 請將您的專案 ID 填入此處
PROJECT_ID = "steady-dryad-478107" 

# 檔案路徑設定
PARSED_INPUT_FILE = Path("data/processed/scholarships_parsed_texts.json")
# ---------------------------------------------

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def upload_to_gcs(storage_client: storage.Client, local_file_path: Path, gcs_destination: str) -> str:
    """將本地檔案上傳到 GCS"""
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(gcs_destination)
    
    # 檢查檔案是否已存在，如果已存在則跳過上傳 (避免重複收費)
    if blob.exists():
        logging.info(f"檔案已存在 GCS: {gcs_destination}. 跳過上傳.")
        return f"gs://{GCS_BUCKET_NAME}/{gcs_destination}"

    blob.upload_from_filename(local_file_path)
    logging.info(f"檔案上傳成功: {local_file_path} -> {gcs_destination}")
    return f"gs://{GCS_BUCKET_NAME}/{gcs_destination}"

def async_batch_annotate_file(
    vision_client: vision.ImageAnnotatorClient, gcs_source_uri: str, gcs_destination_uri: str
) -> longrunning.Operation:
    """對 GCS 上的 PDF/TIFF/圖片執行非同步批次 OCR"""
    
    # 支援的圖片和檔案類型
    lower_uri = gcs_source_uri.lower()
    if lower_uri.endswith(('.pdf', '.tif', '.tiff')):
        mime_type = "application/pdf"
    elif lower_uri.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        # 對單張影像檔，請設定正確的 image/* MIME 類型，
        # 而不是一律使用 image/gif（那會導致 jpeg/png 無法被正確處理）。
        filename = lower_uri.split('/')[-1]
        _, ext = os.path.splitext(filename)
        if ext == '.png':
            mime_type = 'image/png'
        elif ext in ('.jpg', '.jpeg'):
            mime_type = 'image/jpeg'
        elif ext == '.gif':
            mime_type = 'image/gif'
        elif ext == '.bmp':
            mime_type = 'image/bmp'
        else:
            mime_type = 'image/*'
        logging.info(f"影像檔偵測: 設定 MIME 類型 {mime_type}，來源: {gcs_source_uri}")
    else:
        # 不應發生，因為 document_parser 已經篩選過
        logging.warning(f"未知 MIME 類型，跳過 OCR: {gcs_source_uri}")
        return None

    input_config = vision.InputConfig(
        gcs_source=vision.GcsSource(uri=gcs_source_uri),
        mime_type=mime_type,
    )
    
    output_config = vision.OutputConfig(
        gcs_destination=vision.GcsDestination(uri=gcs_destination_uri),
        batch_size=20, # 每次批次處理的頁面數 (僅限 PDF/TIFF)
    )

    feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)

    # 創建單一檔案的 Annotate Request
    annotate_request = vision.AsyncAnnotateFileRequest(
        input_config=input_config,
        features=[feature],
        output_config=output_config,
    )
    
    # 將 Annotate Request 放入列表中，作為 requests 參數的值
    # 這是 vision_client.async_batch_annotate_files 函數的正確輸入格式
    
    logging.info(f"發送非同步 OCR 請求: {gcs_source_uri}")
    return vision_client.async_batch_annotate_files(requests=[annotate_request]) # <--- 將 annotate_request 放入列表中

def download_ocr_results(storage_client: storage.Client, gcs_output_uri: str) -> str:
    """從 GCS 下載 OCR 輸出的 JSON 文件並合併文本"""
    
    bucket_name = gcs_output_uri.split('/')[2]
    prefix = '/'.join(gcs_output_uri.split('/')[3:])
    
    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    
    full_text = []
    
    # OCR 輸出結果會有多個 JSON 檔案 (例如 output-1-to-20.json)
    for blob in blobs:
        if not blob.name.endswith(".json"):
            continue
            
        logging.info(f"下載 OCR 結果 JSON: {blob.name}")
        json_string = blob.download_as_text(encoding="utf-8")
        response = json.loads(json_string)
        
        # 合併所有頁面的文字
        for page_response in response['responses']:
            text = page_response['fullTextAnnotation']['text']
            full_text.append(text)
            
    # 清理 GCS 上的輸出檔案 (可選，但建議清理以控制儲存成本)
    # for blob in blobs:
    #     blob.delete()
        
    return "\n".join(full_text)


def validate_existing_ocr(storage_client: storage.Client, gcs_output_uri: str) -> str:
    """檢查 GCS 上現有的 OCR JSON 是否包含非空文字；若包含則回傳合併後的文字，否則回傳 None。"""
    bucket_name = gcs_output_uri.split('/')[2]
    prefix = '/'.join(gcs_output_uri.split('/')[3:])

    bucket = storage_client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))

    merged_text_parts = []

    for blob in blobs:
        if not blob.name.endswith('.json'):
            continue

        try:
            logging.info(f"驗證現有 OCR 結果 JSON: {blob.name}")
            json_string = blob.download_as_text(encoding="utf-8")
            response = json.loads(json_string)

            for page_response in response.get('responses', []):
                text = page_response.get('fullTextAnnotation', {}).get('text', '')
                if text and text.strip():
                    merged_text_parts.append(text)

        except Exception as e:
            logging.debug(f"無法解析或讀取 {blob.name}: {e}")

    if merged_text_parts:
        return "\n".join(merged_text_parts)
    return None

def main_ocr_processor(only_ids: list = None, only_names: list = None):
    """主函數：處理 OCR 流程"""
    if GCS_BUCKET_NAME == "YOUR_GCS_BUCKET_NAME":
        logging.error("請在腳本中設定正確的 GCS_BUCKET_NAME。")
        return
        
    if not PARSED_INPUT_FILE.exists():
        logging.error(f"找不到已解析的檔案 {PARSED_INPUT_FILE}. 請先運行 document_parser.py")
        return

    # 初始化客戶端 (使用服務帳戶金鑰)
    storage_client = storage.Client.from_service_account_json(SERVICE_ACCOUNT_FILE)
    vision_client = vision.ImageAnnotatorClient.from_service_account_json(SERVICE_ACCOUNT_FILE)
    
    # 1. 讀取解析結果
    with open(PARSED_INPUT_FILE, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)

    def _needs_ocr(item: Dict[str, Any]) -> bool:
        # 如果 parsed_text 為空，無論 status 為何，都視為需要 OCR（優先處理）
        parsed = (item.get('parsed_text') or "").strip()
        if not parsed:
            logging.info(f"parsed_text 為空，將排入 OCR: id={item.get('id')} name={item.get('name')} file={item.get('file_path_local')}")
            return True

        # 否則保留原先的標記邏輯（若被明確標為 OCR_REQUIRED）
        if item.get('status') == 'OCR_REQUIRED':
            return True

        return False

    # 如果 only_ids/only_names 被指定，僅針對那些項目處理。
    def _is_allowed(item: Dict[str, Any]) -> bool:
        if not only_ids and not only_names:
            return True
        if only_ids and str(item.get('id')) in [str(x) for x in only_ids]:
            return True
        # 使用 Unicode 正規化 + casefold 比對檔名片段或檔名
        if only_names:
            def _norm(s: str) -> str:
                return unicodedata.normalize('NFC', (s or '')).strip().casefold()

            lp_raw = item.get('file_path_local', '')
            lp_norm = _norm(lp_raw)
            for nm in only_names:
                nm_norm = _norm(nm)
                if nm_norm in lp_norm:
                    return True
                # 比對 basename
                if _norm(Path(nm).name) == _norm(Path(lp_raw).name):
                    return True
        return False

    ocr_pending_files = [item for item in parsed_data if _needs_ocr(item) and _is_allowed(item)]

    if not ocr_pending_files:
        logging.info("沒有找到需要 OCR 的檔案。流程結束。")
        return

    logging.info(f"找到 {len(ocr_pending_files)} 個檔案需要 OCR 處理。")

    # 2. 執行 OCR 流程
    operations = []
    
    # 2a. 上傳檔案並發起 OCR 請求
    for item in ocr_pending_files:
        local_path = Path(item['file_path_local'])

        # 如果在原始目錄旁有同名 PDF（例如 image.jpg -> image.pdf），則優先上傳 PDF
        preferred_pdf = local_path.with_suffix('.pdf')
        if preferred_pdf.exists():
            upload_path = preferred_pdf
            logging.info(f"找到同名 PDF，將上傳 PDF 而非原始檔: {preferred_pdf}")
        else:
            upload_path = local_path

        # GCS 輸入路徑: ocr_input/[id]_[name].[ext]
        gcs_input_blob = f"{GCS_INPUT_FOLDER}{upload_path.name}"
        gcs_source_uri = upload_to_gcs(storage_client, upload_path, gcs_input_blob)
        
        # GCS 輸出路徑: ocr_output/[id]_[name]_output/
        gcs_output_uri_base = f"gs://{GCS_BUCKET_NAME}/{GCS_OUTPUT_FOLDER}{local_path.stem}_output/"
        
        # 如果 GCS 上已經有 OCR 輸出，先檢查是否包含實際文字；若包含則直接回填，否則重新發送 OCR 請求
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        existing_blobs = list(bucket.list_blobs(prefix=f"{GCS_OUTPUT_FOLDER}{local_path.stem}_output/"))
        if any(b.name.endswith('.json') for b in existing_blobs):
            logging.info(f"找到現有 OCR 輸出，嘗試驗證內容: {gcs_output_uri_base}")
            try:
                validated_text = validate_existing_ocr(storage_client, gcs_output_uri_base)
                if validated_text:
                    logging.info(f"現有 OCR 輸出含有文字，回填並標記為完成: {local_path.name}")
                    item['parsed_text'] = validated_text
                    item['status'] = 'OCR_COMPLETED'
                    # 跳過發送新的 OCR 請求
                    continue
                else:
                    logging.info(f"現有 OCR 輸出沒有偵測到文字，將重新發送 OCR 請求: {gcs_output_uri_base}")
            except Exception as e:
                logging.error(f"驗證現有 OCR 結果失敗 ID {item.get('id')}: {e}")
                # 如果驗證過程有錯誤，我們仍嘗試發送新的 OCR 請求

        operation = async_batch_annotate_file(vision_client, gcs_source_uri, gcs_output_uri_base)

        if operation:
            # 儲存 operation 資訊，以便後續檢查狀態
            operations.append({
                'id': item['id'],
                'name': item['name'],
                # 儲存實際上傳的本機路徑（可能是原始檔，或是同名的 .pdf）
                'local_path': str(upload_path),
                'operation': operation,
                'gcs_output_uri': gcs_output_uri_base,
            })
            
    if not operations:
        logging.warning("沒有成功發起 OCR 操作。請檢查日誌。")
        return

    logging.info(f"已發起 {len(operations)} 個 OCR 請求。等待處理...")

    # 2b. 等待 OCR 完成並下載結果
    
    # 簡易等待迴圈 (實際應用中應使用更精細的重試機制)
    while operations:
        completed_operations = []
        logging.info(f"檢查 OCR 狀態. 剩餘 {len(operations)} 個待處理...")
        time.sleep(30) # 暫停 30 秒等待處理

        # 使用 operations client 正確查詢 long-running operation 狀態
        operations_client = vision_client.transport.operations_client

        for op_info in operations:
            # 先取得 operation 的 name（可能在不同 wrapper 屬性下）
            op_name = getattr(op_info['operation'], 'name', None)
            if op_name is None:
                op_name = getattr(getattr(op_info['operation'], 'operation', None), 'name', None)
            if not op_name:
                logging.warning(f"無法取得 operation 名稱，跳過 ID {op_info['id']}")
                continue

            try:
                op = operations_client.get_operation(op_name)
            except Exception as e:
                logging.error(f"查詢 operation 狀態失敗 ID {op_info['id']}: {e}")
                continue

            if getattr(op, 'done', False):
                logging.info(f"✅ OCR 完成 ID {op_info['id']} - {op_info['name']}")

                try:
                    # 下載並合併 OCR 文本
                    ocr_text = download_ocr_results(storage_client, op_info['gcs_output_uri'])

                    # 3. 回填結果到 parsed_data
                    # 優先以 ID + NAME 完全配對（同一 id 可能有多個檔案）
                    matched = False
                    # helper: normalize names for robust comparison (unicodedata + casefold)
                    def _norm_name(s: str) -> str:
                        return unicodedata.normalize('NFC', (s or '')).strip().casefold()

                    for item in parsed_data:
                        try:
                            if str(item.get('id')) == str(op_info.get('id')):
                                name_a = _norm_name(item.get('name'))
                                name_b = _norm_name(op_info.get('name'))
                                # 若 name 欄位相同，視為完全配對
                                if name_a and name_b and name_a == name_b:
                                    item['parsed_text'] = ocr_text
                                    item['status'] = 'OCR_COMPLETED'
                                    matched = True
                                    break
                        except Exception:
                            continue

                    # 若未找到 id+name 的完全配對，回退到較寬鬆的配對（id 或檔案路徑匹配）
                    if not matched:
                        for item in parsed_data:
                            try:
                                if str(item.get('id')) == str(op_info.get('id')):
                                    item['parsed_text'] = ocr_text
                                    item['status'] = 'OCR_COMPLETED'
                                    matched = True
                                    break
                            except Exception:
                                pass

                            fp = item.get('file_path_local')
                            # 也比較標準化後的同名 PDF 路徑
                            if fp:
                                try:
                                    if fp == op_info.get('local_path') or str(Path(fp).with_suffix('.pdf')) == op_info.get('local_path'):
                                        item['parsed_text'] = ocr_text
                                        item['status'] = 'OCR_COMPLETED'
                                        matched = True
                                        break
                                except Exception:
                                    continue

                    if not matched:
                        logging.warning(f"回填失敗：找不到對應的 parsed_data 條目 (id={op_info.get('id')} name={op_info.get('name')} local={op_info.get('local_path')})")

                    completed_operations.append(op_info)

                except Exception as e:
                    logging.error(f"下載或回填失敗 ID {op_info['id']}: {e}")
                    # 如果失敗，將其標記為錯誤，避免重複重試
                    # 標記失敗時也使用相同的配對邏輯：優先 id+name，否則回退到 id 或路徑
                    failed_marked = False
                    def _norm_name(s: str) -> str:
                        return unicodedata.normalize('NFC', (s or '')).strip().casefold()

                    for item in parsed_data:
                        try:
                            if str(item.get('id')) == str(op_info.get('id')):
                                name_a = _norm_name(item.get('name'))
                                name_b = _norm_name(op_info.get('name'))
                                if name_a and name_b and name_a == name_b:
                                    item['status'] = 'OCR_FAILED'
                                    item['parsed_text'] = f"[OCR_FAILED: {e}]"
                                    failed_marked = True
                                    break
                        except Exception:
                            continue

                    if not failed_marked:
                        for item in parsed_data:
                            try:
                                if str(item.get('id')) == str(op_info.get('id')):
                                    item['status'] = 'OCR_FAILED'
                                    item['parsed_text'] = f"[OCR_FAILED: {e}]"
                                    failed_marked = True
                                    break
                            except Exception:
                                pass

                            fp = item.get('file_path_local')
                            if fp:
                                try:
                                    if fp == op_info.get('local_path') or str(Path(fp).with_suffix('.pdf')) == op_info.get('local_path'):
                                        item['status'] = 'OCR_FAILED'
                                        item['parsed_text'] = f"[OCR_FAILED: {e}]"
                                        failed_marked = True
                                        break
                                except Exception:
                                    continue

                    if not failed_marked:
                        logging.warning(f"無法為失敗的 OCR 操作找到對應的 parsed_data 條目 (id={op_info.get('id')} name={op_info.get('name')} local={op_info.get('local_path')})")
                    completed_operations.append(op_info)
        
        # 從待處理清單中移除已完成的
        operations = [op for op in operations if op not in completed_operations]
        
    logging.info("所有 OCR 操作檢查完畢。")

    # 4. 儲存更新後的 JSON (使用更穩健的原子寫入機制)
    # -----------------------------------------------
    # 寫入流程：
    # 1) 在相同目錄建立一個 NamedTemporaryFile，寫入並 fsync
    # 2) 將原始檔案備份為 .bak（如果存在）
    # 3) 用 os.replace 原子性地取代原始檔案
    # 4) 寫入失敗時嘗試還原備份並清理臨時檔案
    import tempfile

    TEMP_OUTPUT_FILE = None
    BACKUP_FILE = PARSED_INPUT_FILE.with_suffix('.json.bak')

    try:
        logging.info(f"開始穩健原子寫入到臨時檔案 (dir={PARSED_INPUT_FILE.parent}): {PARSED_INPUT_FILE.name}.tmp")

        # 在同一個目錄下建立暫存檔，避免跨檔案系統 rename 問題
        tf = tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=str(PARSED_INPUT_FILE.parent), delete=False, prefix=PARSED_INPUT_FILE.stem + '-', suffix='.json.tmp')
        TEMP_OUTPUT_FILE = Path(tf.name)

        try:
            json.dump(parsed_data, tf, ensure_ascii=False, indent=4)
            tf.flush()
            os.fsync(tf.fileno())
        finally:
            tf.close()

        # 備份原始檔案（如果存在）
        if PARSED_INPUT_FILE.exists():
            try:
                os.replace(PARSED_INPUT_FILE, BACKUP_FILE)
            except Exception as e:
                logging.warning(f"無法建立備份 {BACKUP_FILE}: {e}")

        # 原子性替換
        os.replace(str(TEMP_OUTPUT_FILE), str(PARSED_INPUT_FILE))

        # 如果替換成功，移除備份（可選）
        if BACKUP_FILE.exists():
            try:
                os.remove(BACKUP_FILE)
            except Exception:
                logging.debug(f"無法刪除備份檔案 {BACKUP_FILE}（可忽略）")

        logging.info(f"🎉 數據集已安全更新 OCR 結果並保存到 {PARSED_INPUT_FILE}")

    except Exception as e:
        logging.error(f"❌ 警告：無法進行穩健原子寫入: {e}")
        # 嘗試還原備份（如果存在且目標檔案缺失）
        try:
            if BACKUP_FILE.exists() and not PARSED_INPUT_FILE.exists():
                os.replace(BACKUP_FILE, PARSED_INPUT_FILE)
                logging.info(f"已還原備份到 {PARSED_INPUT_FILE}")
        except Exception as e2:
            logging.error(f"還原備份失敗: {e2}")

        # 嘗試刪除臨時檔案
        try:
            if TEMP_OUTPUT_FILE and TEMP_OUTPUT_FILE.exists():
                os.remove(TEMP_OUTPUT_FILE)
        except Exception:
            pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cloud OCR processor - optionally target specific IDs or filenames')
    parser.add_argument('--only-ids', help='Comma-separated list of IDs to process (e.g. 7669,7720)', default='')
    parser.add_argument('--only-names', help='Comma-separated list of filename fragments or basenames to process (e.g. 海報.jpg,填寫範例.jpg)', default='')
    args = parser.parse_args()

    only_ids = [x.strip() for x in args.only_ids.split(',') if x.strip()] if args.only_ids else None
    only_names = [x.strip() for x in args.only_names.split(',') if x.strip()] if args.only_names else None

    main_ocr_processor(only_ids=only_ids, only_names=only_names)
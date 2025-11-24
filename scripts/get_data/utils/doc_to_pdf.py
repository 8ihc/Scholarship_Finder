# doc_converter.py
"""
將舊版 Word 檔案 (.doc) 轉換為 .pdf 格式。
由於 Python 無法原生可靠地解析 .doc 格式，此腳本依賴外部的 LibreOffice/OpenOffice 命令行工具。
轉換後的 .pdf 文件將被儲存到 CONVERSION_DIR，然後可以被 document_parser.py 重新處理。
"""
import argparse
import os
import subprocess
import time
from pathlib import Path

# --- Configuration ---
# 原始的 .doc 檔案位置
ATTACHMENTS_DIR = Path("data/raw/attachments")
# 轉換後檔案的輸出位置 (與原始目錄相同，方便 document_parser 重新掃描)
CONVERSION_OUTPUT_DIR = ATTACHMENTS_DIR 
# ---------------------

# Windows 和 Linux 上常見的 LibreOffice/soffice 執行檔路徑 (需根據您的安裝情況調整)
DEFAULT_SOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/libreoffice",
    "/usr/local/bin/libreoffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]

def find_soffice_path(custom_path=None):
    """嘗試尋找 LibreOffice/soffice 的執行檔路徑"""
    paths_to_check = [custom_path] if custom_path else DEFAULT_SOFFICE_PATHS
    
    for path in paths_to_check:
        if path and Path(path).is_file():
            print(f"找到 LibreOffice 執行檔: {path}")
            return path
    
    print("錯誤: 找不到 LibreOffice/soffice 執行檔。")
    print("請確認您已安裝 LibreOffice，並使用 --soffice-path 參數指定正確的路徑。")
    return None

def convert_doc_files(soffice_path: str, output_format: str = 'pdf'):
    """遍歷附件目錄，將所有 .doc 檔案轉換為指定格式"""
    
    doc_files = list(ATTACHMENTS_DIR.glob('*.doc'))
    
    if not doc_files:
        print("未找到任何 .doc 檔案需要轉換。")
        return
        
    print(f"--- 開始轉換 {len(doc_files)} 個 .doc 檔案為 .{output_format} ---")
    
    # 創建輸出目錄 (如果 CONVERSION_OUTPUT_DIR 與 ATTACHMENTS_DIR 相同則無需額外創建)
    CONVERSION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    
    for doc_file in doc_files:
        # LibreOffice 轉換參數
        # --headless: 在沒有 GUI 的情況下運行
        # --convert-to [format]: 指定輸出格式 (例如 pdf, docx)
        # --outdir [directory]: 指定輸出目錄
        command = [
            soffice_path,
            '--headless',
            '--convert-to', output_format,
            '--outdir', str(CONVERSION_OUTPUT_DIR),
            str(doc_file)
        ]
        
        print(f"\n[處理 ID: {doc_file.stem.split('_')[0]}] 轉換: {doc_file.name}")
        
        try:
            # 執行命令，設置較長的 timeout 以應對大檔案
            result = subprocess.run(command, capture_output=True, text=True, timeout=600, encoding='utf-8', check=True)
            
            # 檢查輸出檔案是否成功生成 (檔名會變成 [ID]_[Name].[output_format])
            expected_output_name = doc_file.stem + f'.{output_format}'
            expected_output_path = CONVERSION_OUTPUT_DIR / expected_output_name
            
            if expected_output_path.is_file() and expected_output_path.stat().st_size > 0:
                # 為了避免 document_parser 遇到舊檔名，我們將原始的 .doc 檔案重新命名
                # 這樣下次運行時就不會再次嘗試轉換
                archive_path = doc_file.with_suffix('.doc_archive')
                doc_file.rename(archive_path)
                
                print(f"  ✅ 轉換成功: {expected_output_path.name}")
                print(f"  (原始檔案已重新命名為: {archive_path.name})")
                success_count += 1
            else:
                print(f"  ❌ 轉換失敗: 輸出檔案 {expected_output_path.name} 未生成或為空。")
                print(f"  (LibreOffice 輸出: {result.stdout.strip()})")

        except subprocess.CalledProcessError as e:
            print(f"  ❌ 命令執行錯誤: {e.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"  ❌ 轉換超時 (超過 600 秒)。")
        except Exception as e:
            print(f"  ❌ 發生未知錯誤: {e}")
            
        time.sleep(0.5) # 稍微延遲

    print("\n" + "="*50)
    print(f"轉換完成。成功: {success_count}/{len(doc_files)} 筆")
    print(f"請重新運行 document_parser.py 來解析新的 .{output_format} 檔案。")
    print("="*50)


def main():
    parser = argparse.ArgumentParser(description='Convert .doc files to PDF/DOCX using LibreOffice.')
    parser.add_argument('--soffice-path', type=str, help='Path to the soffice/libreoffice executable.')
    parser.add_argument('--format', type=str, default='pdf', choices=['pdf', 'docx'], help='Output format (pdf or docx). Default is pdf.')
    
    args = parser.parse_args()
    
    # 尋找 LibreOffice 路徑
    soffice_path = find_soffice_path(args.soffice_path)
    
    if soffice_path:
        convert_doc_files(soffice_path, args.format)

if __name__ == "__main__":
    main()
# 獎學金爬蟲使用說明

## 檔案說明

- `scripts/scrape_scholarships.py` - 爬取台大獎學金列表和詳細資料
- `scripts/analyze_clarity.py` - 分析申請資格欄位的清晰度

## 功能特點

✅ **自動分頁爬取**：從指定頁面開始爬取，支援 1-30 頁（共 300 筆資料）  
✅ **即時寫入**：每頁爬完立即寫入 CSV，避免網路中斷導致資料遺失  
✅ **斷點續爬**：自動檢測已爬取的資料，跳過重複項目  
✅ **錯誤重試**：網路錯誤自動重試，單筆失敗不影響整體進度  
✅ **進度追蹤**：即時顯示爬取進度和統計資訊  

## 基本使用

### 從頭開始爬取 300 筆資料（30 頁）

```powershell
cd c:\Users\8ihc8\Desktop\scholarship
python scripts\scrape_scholarships.py
```

### 從特定頁面開始（例如從第 10 頁開始）

```powershell
python scripts\scrape_scholarships.py --start-page 10
```

### 顯示瀏覽器視窗（調試用）

```powershell
python scripts\scrape_scholarships.py --no-headless
```

## 進階參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `--output-file` | `data/classification_results.csv` | 輸出檔案路徑 |
| `--start-page` | `1` | 開始爬取的頁數 |
| `--max-pages` | `30` | 最多爬取幾頁 |
| `--delay` | `1.0` | 每次請求間隔（秒） |
| `--timeout` | `30000` | 請求逾時時間（毫秒） |
| `--retry` | `2` | 失敗重試次數 |
| `--headless` / `--no-headless` | `--headless` | 是否隱藏瀏覽器視窗 |

### 範例：快速爬取（縮短延遲）

```powershell
python scripts\scrape_scholarships.py --delay 0.5
```

### 範例：爬取前 10 頁

```powershell
python scripts\scrape_scholarships.py --max-pages 10
```

### 範例：增加穩定性（延長等待和重試）

```powershell
python scripts\scrape_scholarships.py --delay 2.0 --retry 3 --timeout 60000
```

## 資料恢復機制

### 情境 1：網路中斷

假設爬到第 15 頁時網路中斷：

1. **已完成的資料安全**：第 1-14 頁的資料已寫入 CSV
2. **恢復爬取**：
   ```powershell
   python scripts\scrape_scholarships.py --start-page 15
   ```
3. **自動去重**：腳本會自動跳過已存在的 ID

### 情境 2：程式崩潰

假設程式在第 20 頁崩潰：

1. **檢查檔案**：查看 `data/classification_results.csv`，確認最後完成的頁數
2. **重新執行**：
   ```powershell
   # 如果完成到第 19 頁，從第 20 頁重新開始
   python scripts\scrape_scholarships.py --start-page 20
   ```

### 情境 3：部分資料爬取失敗

某些獎學金可能因為伺服器問題爬取失敗（標記為「抓取失敗」）：

1. **完成整體爬取**
2. **檢查失敗項目**：
   ```powershell
   python -c "import pandas as pd; df = pd.read_csv('data/classification_results.csv', encoding='utf-8-sig'); print(df[df['外部申請網站'].str.contains('抓取失敗', na=False)])"
   ```
3. **手動處理**：記錄失敗的 ID，稍後單獨處理

## 輸出格式

CSV 檔案包含以下欄位：

| 欄位 | 說明 |
|------|------|
| ID | 獎學金編號 |
| URL | 詳細頁面網址 |
| 外部申請網站 | 外部申請連結 |
| 類別名稱 | 獎學金類別 |
| 申請日期 | 申請期限 |
| 獎學金名稱 | 獎學金全名 |
| 申請地點 | 申請地點 |
| 附加檔案 | 附件連結（格式：檔名 [URL]） |
| 獎學金金額 | 獎學金金額 |
| 獎學金名額 | 名額限制 |
| 申請對象 | 申請對象描述 |
| 申請資格 | 申請資格詳細說明 |
| 繳交文件 | 需繳交的文件 |
| 爬取頁數 | 該筆資料來自第幾頁 |
| 爬取時間 | 爬取時間戳記 |

## 爬取策略建議

### 方案 1：一次性完整爬取（推薦）

```powershell
# 連續爬取 30 頁，預計 10-15 分鐘
python scripts\scrape_scholarships.py
```

### 方案 2：分段爬取（穩定網路環境較差時）

```powershell
# 第一批：前 10 頁
python scripts\scrape_scholarships.py --max-pages 10

# 第二批：第 11-20 頁
python scripts\scrape_scholarships.py --start-page 11 --max-pages 10

# 第三批：第 21-30 頁
python scripts\scrape_scholarships.py --start-page 21 --max-pages 10
```

### 方案 3：測試爬取（首次使用）

```powershell
# 先爬 2 頁測試
python scripts\scrape_scholarships.py --max-pages 2 --no-headless

# 確認無誤後繼續
python scripts\scrape_scholarships.py --start-page 3
```

## 注意事項

1. **禮貌爬取**：預設延遲 1 秒，請勿調太低以避免對伺服器造成負擔
2. **檔案編碼**：輸出使用 UTF-8-BOM 編碼，Excel 可直接開啟
3. **去重機制**：基於 ID 欄位去重，相同 ID 只會保留第一次爬取的資料
4. **錯誤處理**：個別獎學金爬取失敗不會中斷整體流程
5. **時間戳記**：每筆資料記錄爬取時間，方便追蹤

## 常見問題

### Q: 可以同時執行多個爬蟲實例嗎？

**不建議**。同一個 CSV 檔案無法同時寫入。如需加速，請使用不同的輸出檔案：

```powershell
# 實例 1：爬取第 1-15 頁
python scripts\scrape_scholarships.py --max-pages 15 --output-file data/part1.csv

# 實例 2：爬取第 16-30 頁
python scripts\scrape_scholarships.py --start-page 16 --max-pages 15 --output-file data/part2.csv

# 合併檔案
python -c "import pandas as pd; pd.concat([pd.read_csv('data/part1.csv', encoding='utf-8-sig'), pd.read_csv('data/part2.csv', encoding='utf-8-sig')]).to_csv('data/classification_results.csv', index=False, encoding='utf-8-sig')"
```

### Q: 如何知道目前爬了多少筆？

```powershell
python -c "import pandas as pd; df = pd.read_csv('data/classification_results.csv', encoding='utf-8-sig'); print(f'已爬取 {len(df)} 筆資料')"
```

### Q: 網頁結構改變導致爬取失敗怎麼辦？

檢查錯誤訊息，如果是 CSS selector 找不到元素，需要更新 `scrape_scholarships.py` 中的 `extract_fields()` 或 `extract_scholarship_ids_from_list_page()` 函數。

## 下一步

爬取完成後，可以執行：

```powershell
# 分析申請資格完整性
python analyze_qualification_completeness.py

# 下載需要補充的獎學金附件
python scripts\process_attachments.py --ids 7644,7851,7837,7747,7798,7871,7873,7862
```

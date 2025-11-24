# **Proposal | NTU Scholarship Finder**

## **專案描述**

### **要解決什麼問題？**

現行的[台大獎學金公告一覽表](https://advisory.ntu.edu.tw/CMS/Scholarship?pageId=232&keyword=&applicant_type=16&sort=f_apply_start_date&pageIndex=1&show_way=all)存在以下問題：

1. **資訊分散難搜尋**：獎學金詳細資訊散落在各網頁，甚至藏在附加檔案文件或外部連結中，學生需要花費大量時間逐一查看  
2. **分類標籤失效**：原網站雖提供身分標籤（包含身障、碩士、博士、大學部、一般生、清寒、大一新生、原住民、僑生、陸生、特殊境遇），但篩選功能不準確。例如選擇「一般生」後仍出現需清寒證明的獎學金  
3. **隱形經濟困難難以匹配**：因分類標籤失效，導致有實際經濟困難者但不符合官方「特殊身分」定義的學生，難以從現有標籤中找到適合的獎學金  
4. **申請評估成本高**：實際需要經濟支持的學生，得先逐一理解各獎學金的申請資格與條件，在時間有限的情況下，容易錯過更適合自己的機會

### **目標使用者是誰？**

* **主要使用者**：台大在學學生（大學部、碩士、博士生）  
* **特別關注**：  
  * 有實際經濟壓力（如家庭收入不穩定、醫療支出等），但無法取得官方認定的經濟相關身分者（如清寒、中低收入戶）  
  * 不熟悉獎學金申請流程、時間有限或資訊搜尋能力較弱的學生

### **價值在哪？**

* **節省時間並提升成功率**：透過關鍵詞分析與結構化標籤，學生可在數秒內篩選出符合條件的獎學金，而不必逐一點開附件（或外部網站）。此舉將減少搜尋與閱讀成本，讓更多學生能在申請期限內完成準備。  
* **促進教育公平與資訊可及性**：幫助「隱形經濟困難」的學生找到適合的獎學金，同時降低資訊落差，讓真正需要幫助的學生，也能有被看見與被支持的機會。

## **使用者故事**

### **Story 1: 隱形經濟困難學生**

**As a** 父母僅能支援基本生活費，但需要額外自費醫療（如心理諮商或物理治療）的學生  
**I want** 透過填選或勾選我的身分與需求（例如：學制、經濟狀況、科系）來篩出適合的獎學金清單  
**So that** 我能在短時間內找到最有可能提供實際幫助的獎學金並準備申請文件

### **Story 2: 時間有限的研究生**

**As a** 忙於研究、又需兼職維持生活費，沒有時間逐一瀏覽各獎學金公告的研究生  
**I want** 透過簡單的篩選選項（例如獎學金金額、申請截止日、是否需要家庭經濟證明）快速過濾掉不合適的獎學金  
**So that** 我能專注於研究與課業，同時不錯過潛在的經濟支援機會

### **Story 3: 來自偏鄉、缺乏資訊管道的學生**

**As a** 來自偏鄉、從未接觸過獎學金申請資訊，也不熟悉（學校）行政流程的學生  
**I want** 前端有清楚的標籤與篩選介面（checkbox \+ 簡單說明），並能看到每筆獎學金的必要文件  
**So that** 即使我沒有經驗，也能順利找到可申請的獎學金並依清單準備文件

## **系統前期準備**

在建立可供使用者操作的介面之前，系統需先完成資料基礎建構。本階段的目標是建立一份乾淨且結構化的獎學金資料庫，並根據資料特徵設計後續前端的篩選標籤。

### **步驟 1：獎學金資料蒐集**

**描述**：蒐集約 100–200 筆來自[台大獎學金公告一覽表](https://advisory.ntu.edu.tw/CMS/Scholarship?pageId=232&keyword=&applicant_type=16&sort=f_apply_start_date&pageIndex=1&show_way=all)的資料。爬取內容包含獎學金 ID、獎學金 URL、類別名稱、獎學金名稱、申請日期、申請地點、獎學金金額、獎學金名額、申請對象、申請資格、繳交文件、附加檔案（含下載連結）、外部申請網站 URL。所有資料以CSV 及 JSON 格式輸出與儲存。（此階段已完成初步測試，成功建立具完整欄位的 20 筆原始資料集）

**輸入**：

* [台大獎學金公告一覽表](https://advisory.ntu.edu.tw/CMS/Scholarship?pageId=232&keyword=&applicant_type=16&sort=f_apply_start_date&pageIndex=1&show_way=all)

**輸出**：

* data/raw\_scholarships.json  
* 以下為測試資料範例

```json
{
  "id": "7644",
  "url": "https://advisory.ntu.edu.tw/CMS/ScholarshipDetail?id=7644",
  "external_links": [
    "https://www.mol.gov.tw/topic/23616/",
    "https://www.tipo.gov.tw/ct.asp?xItem=206783&ctNode=6991&mp=1",
    "https://www.cdffoundation.org",
"https://www.cdffoundation.org/zh-tw/scholarships/vocational-education-scholarship"
  ],
  "category": "法人暨私設",
  "apply_date": "自2025/1/22起至2025/12/31止",
  "title": "114年度『財團法人中華開發文教基金會「技藝職能獎學金」』",
  "apply_location": "逕寄掛號：105021台北市松山區敦化北路135號12樓「財團法人中華開發文教基金會」收（註明：技藝職能獎學金計畫）",
  "attachments": [
    {
      "file_name": "辦法及專用申請書",
      "url": "https://advisory.ntu.edu.tw/CMS/GetScholarshipFile/6411"
    }
  ],
  "amount": "未定",
  "quota": "未定",
  "applicant": "身障生、碩士生、博士生、大學部、一般生、清寒、原住民、特殊境遇",
  "eligibility": "請詳閱辦法或網站辦理申請：https://www.cdffoundation.org https://www.cdffoundation.org/zh-tw/scholarships/vocational-education-scholarship",
  "required_docs": "-"
}
```

### **步驟 2：欄位品質檢查、資料整合與資料清洗**

**描述**：

在人工檢視 20 筆樣本資料後，歸納出「申請資格」欄位的常見書寫模式，並建立一套 rule-based 規則，用以自動判斷「申請資格」欄位的敘述是否清晰（clear / unclear / not\_certain）。

若公告內容中「申請資格」模糊不明（例如以「依附件辦法為準」或「詳見官方網站」表示），系統會標記為 unclear 或 not\_certain，並在 reason 欄位中紀錄原因說明（例如「需查看附件」、「需訪問外部網站」等）。

在資料整合階段，系統不僅會下載標示為 not clear 或 uncertain 的附加檔案，還會嘗試解析其中的文字內容（如 PDF 或 ODT），將結果回填至主資料表中相應欄位。這樣設計可確保所有來源（主頁、附件、外部網站）最終都能整合回同一筆獎學金資料中，並可溯源至原始文件或連結。

在此基礎上，系統進一步進行資料清洗與欄位精簡，從原始資料中挑選並重新命名主要欄位，以建立可直接使用的分析資料表。

| 資料 not clear / uncertain 類型 | 問題 | 實務對策 |
| ----- | ----- | ----- |
| **附加檔案（可能需 OCR）** | 主頁只放摘要，實際申請資訊藏在附加檔案裡。 | 系統下載標記為 unclear/not\_certain 的附檔，依格式（PDF/ODT）嘗試文字擷取。 若擷取成功，則建立 parsed\_text 欄位，儲存 OCR 或文字解析結果。 若該內容中包含申請資格、金額、日期等欄位資訊，則會以 rule-based 或關鍵字比對方式回填至主資料中。 若解析失敗，則僅保留 local\_path 供人工審閱。 |
| **外部連結（需跳轉）** | 主頁只放摘要，實際資訊藏在外部連結。 | 系統對可信任來源執行一次跳轉爬取。 若成功擷取到獎學金詳細說明或申請條件，則建立 external\_text 欄位儲存原始文字，並同樣回填主欄位。 若目標為表單或雲端文件（無法解析），則僅保留 URL 與來源說明。 |

**輸入**：

* data/raw\_scholarships.json

**輸出**：

* data/scholarships\_cleaned.json（經清洗與標記後的資料）  
* docs/rules\_description.md（Rule-based 規則與清洗邏輯說明文件）  
* data/scholarship\_files\_unclear/（僅儲存 unclear 或 uncertain 的附加檔案）

### **步驟 3：高頻詞分析與標籤設計**

**描述**：

根據已結構化的 100–200 筆資料進行關鍵詞統計與同義詞歸類，找出最具代表性的分類維度（如學制、系級、成績、官方認定身分如身障與中低收入戶、本地/外國、金額範圍、申請方式等），歸納出前端介面中要使用的 8–12 個主要篩選標籤。

**輸入**：

* data/scholarships\_cleaned.json（經清洗與標記後的資料）

**輸出**：

* 詞頻與欄位統計報告（docs/analysis\_report.md）  
* 前端 MVP 標籤建議清單（data/schema/tag\_suggestions.json）

## **主要功能 (MVP)**

### **功能 1: 條件篩選查詢**

**描述**：使用者透過前端介面勾選或填寫篩選條件（如學制、身分、金額範圍、戶籍地、成績等），系統即時從已整理好的獎學金資料庫中篩選出符合條件的獎學金清單。

**輸入**：

```
- 學制：大學部 
- 科系：政治系 
- 學級：三年級 
- 上一學年成績：GPA 4.0 
- 戶籍地：雲林 
- 官方認定身分：一般生（非清寒、非中低收入戶） 
- 獎學金金額：> 10,000 元 
- 申請截止日：2025/11/30 之前
```

**輸出**：

```
- 符合條件的獎學金清單，每筆顯示： 
  - 獎學金名稱 
  - 金額與名額 
  - 申請起訖日期 
  - 申請資格摘要 
  - 支援排序：截止日近→遠、金額高→低 
```

### **功能 2: 查看獎學金詳細資訊**

**描述**：使用者點選清單中的某筆獎學金後，系統展開完整的詳細資訊，包括完整申請資格、繳交文件清單、申請地點、附加檔案下載連結、原始公告 URL、獎學金官方網站 URL（如有）等。

**輸入**：

```
- 點選獎學金：「雲林縣同鄉會獎學金」 
```

**輸出**：

```
- 獎學金完整資訊：
  - 申請資格：雲林縣籍、大學部、GPA 3.5 以上、操行優等
  - 繳交文件：成績單正本、戶籍謄本、自傳、申請表
  - 申請地點：郵寄至雲林縣同鄉會辦公室
  - 附加檔案：[下載申請表 PDF]
  - 原始公告：[台大獎學金公告連結]
  - 官方網站：[雲林縣同鄉會獎學金專頁]
```

### **功能 3: 繳交文件清單整合**

**描述**：當使用者同時查看多筆獎學金時，系統可將這些獎學金所需的「繳交文件」整合成一份 checklist，幫助使用者一次準備所有文件，避免重複作業。

**輸入**：

```
- 已選取的獎學金： 
  1. 雲林縣同鄉會獎學金 
  2. 教育發展獎學金 
  3. 學業優良獎學金 
  4. 夢想助學金 
  5. 優秀學生獎學金
```

**輸出**：

```
📋 文件準備清單
  □ 成績單正本 x 5 
  □ 成績單影本 x 2 
  □ 戶籍謄本影本 x 3 
  □ 自傳 x 3 
  □ 申請表 x 5（各獎學金專用） 
  □ 推薦信 x 2 
  □ 家庭收入證明 x 1
💡 提示：建議先準備較多數量的通用文件（如成績單、戶籍謄本）
```

## **Tech Stack**

### **主要套件 (Key Packages)** 

```
playwright==1.40.0
requests==2.31.0
beautifulsoup4==4.12.0
pandas==2.0.0
python-dateutil==2.8.0
pdfplumber==0.10.0
pytesseract==0.3.10
python-docx==0.8.11
odfpy==1.4.2
openpyxl==3.1.0
jieba==0.42.1
```

### **後端（Backend / Data Processing）**

這部分負責**資料蒐集、解析、清洗與結構化**，是整個系統的核心。

| 模組分類 | 套件 | 功能說明 |
| ----- | ----- | ----- |
| **網頁爬蟲與資料擷取** | playwright, beautifulsoup4, requests | 動態網頁抓取、HTML 解析、附加檔案與外部連結下載 |
| **資料處理與分析** | pandas, python-dateutil, re jieb\`, spaCy, scikit-learn | 資料清理與格式化、欄位抽取、日期標準化、關鍵詞分析（TF-IDF、詞頻、同義詞歸類）、簡易分群 |
| **PDF 與文件處理** | pdfplumber, pytesseract, python-docx, odfpy | 解析附件（PDF、DOCX、ODT）內容並回填主資料 |
| **資料匯出與格式支援** | openpyxl, csv, json, os, datetime, argparse, urllib.parse | 匯出結果、整理輸出格式、建立 CLI 操作介面 |

### **前端（Frontend / User Interface）**

| 模組分類 | 套件 | 功能說明 |
| ----- | ----- | ----- |
| **介面原型** | Streamlit 或 Flask \+ Bootstrap | 建立篩選與查詢介面，讓使用者勾選條件並查看結果 |
| **資料展示與互動** | JavaScript（選用） | 若採靜態網頁展示，可加上前端互動與排序功能 |

## **檔案結構**

```
scholarship-lens/
│
├── README.md
├── PROPOSAL.md
├── requirements.txt
│
├── src/
│   ├── main.py                     # 主控制腳本：整合執行流程
│   │
│   ├── scrapers/                   # Step 1：資料爬取
│   │   └── ntu_scraper.py
│   │
│   ├── parsers/            	    # Step 2：內容解析（HTML / PDF / ODT）
│   │   ├── html_parser.py
│   │   ├── pdf_parser.py
│   │   ├── odt_parser.py
│   │   └── text_cleaner.py
│   │
│   ├── processor/                  # Step 3：資料清洗與整合
│   │   ├── data_cleaner.py
│   │   ├── rule_based_checker.py
│   │   └── file_integrator.py      # 附檔/外部連結整合與回填
│   │
│   ├── analyzer/                   # Step 4：文字分析與標籤生成 (NLP)
│   │   ├── keyword_analyzer.py     # jieba / TF-IDF / scikit-learn
│   │   ├── tag_designer.py         # 建立前端可用的標籤 schema
│   │   └── report_generator.py     # 匯出 analysis_report.md
│   │
│   ├── frontend/                   # Step 5：展示與互動
│   │   ├── app.py                  # Streamlit 或 Flask 主程式
│   │   └── static/                 # HTML/CSS/JS（若需）
│   │
│   └── utils/
│       ├── data_manager.py
│       └── file_utils.py
│
├── data/
│   ├── raw/                        # 原始/外部 HTML / PDF / ODT
│   ├── processed/                  # 清洗後的中間資料（JSON / CSV）
│   ├── integrated/                 # 已整合附檔與外部連結後的最終資料
│   ├── schema/                     # 欄位說明與標籤 mapping
│   └── scholarship_files_unclear/  # 不可解析 / 需人工審查的附件
│
├── docs/
│   ├── rules_description.md
│   ├── analysis_report.md
│   └── tag_design.md
│
└── tests/
    ├── test_scraper.py
    ├── test_parser.py
    └── test_analyzer.py


```

## **範例**

**情境說明**：

```
小明是台大政治系大三學生，基本生活費不穩定但不具清寒或中低收入戶身分。他勾選「大學部」「一般生」「獎學金金額 > 10,000」「（戶籍地）雲林」「成績 GPA 4.0」等條件後，系統即回傳「雲林縣同鄉會獎學金」與「教育發展獎學金」，並顯示詳細申請資格、截止日期與申請文件清單。小明可直接下載附加檔案或前往官方網站申請。
```

**步驟 1：基本篩選查詢、顯示搜尋結果**

```
小明進入 NTU Scholarship Finder 首頁，透過勾選、下拉或滑桿方式設定以下條件：
- 學制：大學部
- 科系：政治系
- 學級：三年級
- 上一學年成績：GPA 4.0
- 戶籍地：雲林
- 官方認定身分：一般生（非清寒、非中低收入戶）
- 獎學金金額：> 10,000 元
- 申請截止日：2025/11/30 之前
- ...

系統即時從 `data/integrated/scholarships_final.json` 讀取並篩選，回傳符合條件的獎學金清單： 
- 雲林縣同鄉會獎學金（20,000 元 / 截止日 2025-11-15） 
- 教育發展獎學金（15,000 元 / 截止日 2025-11-30） 
- ...
```

**步驟 2：查看獎學金詳細資訊**

```
小明點選「雲林縣同鄉會獎學金」的「查看詳細」按鈕，系統展開完整資訊：

- **申請資格**：雲林縣籍、大學部、GPA 3.5 以上、家庭年收入 < 100 萬
- **繳交文件**：成績單正本、戶籍謄本、自傳、申請表
- **申請地點**：雲林縣同鄉會辦公室
- **附加檔案**：[下載申請表 PDF]
- **原始公告**：https://advisory.ntu.edu.tw/CMS/ScholarshipDetail?id=xxxx
- **官方網站**：https://yunlin-scholarship.org.tw

小明確認自己符合條件，決定申請。
```

**步驟 3：繳交文件清單整合**

```
小明同時想申請「雲林縣同鄉會獎學金」和「教育發展獎學金」，他勾選這兩筆獎學金後，點選「整合文件清單」按鈕。

系統回傳：
📋 文件準備清單
□ 成績單正本 x 2 
□ 戶籍謄本 x 2 
□ 自傳 x 2 
□ 申請表 x 2（各獎學金專用，請分別下載） □ 推薦信 x 1
💡 提示：兩份獎學金的申請截止日不同，請注意時程安排

小明依此清單準備文件，並直接從系統下載申請表或前往官方網站申請。
```

---

**最後更新**: 2025-10-11  
 **版本**: v1.0 (MVP Proposal)


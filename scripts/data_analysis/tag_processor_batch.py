import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field, ValidationError
from typing import List, Literal, Optional, Any

# --- 1. 配置與初始化 ---
MODEL_NAME = 'gemini-2.5-flash'

# ！！！新的 Vertex AI 模式初始化 ！！！
# 請替換為您的 GCP 專案 ID 和模型區域 (Region)
PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
REGION = os.environ.get("GCP_REGION")  # 例如 "us-central1" 或 "asia-east1"

if not PROJECT_ID or not REGION:
    print("錯誤：PROJECT_ID 或 REGION 環境變數未設定。")
    print("請設定 GCP_PROJECT_ID 和 GCP_REGION 變數後再執行。")
    exit()

try:
    client = genai.Client(
        vertexai=True,           # 啟用 Vertex AI 模式
        project=PROJECT_ID,
        location=REGION
    )
except Exception:
    print("錯誤：無法初始化 Vertex AI Client。請檢查 PROJECT_ID, REGION，以及 GOOGLE_APPLICATION_CREDENTIALS 環境變數是否正確設定。")
    raise # 在無法連接時拋出錯誤，確保程序停止。


# --- 2. 最終版 19 個類別定義 (用於 Pydantic Literal 限制) ---
CATEGORIES = Literal[
    "學制", "年級", "學籍狀態", "學院", 
    "國籍身分", "設籍地", "就讀地", 
    "特殊身份", "家庭境遇","經濟相關證明", 
    "核心學業要求", "操行/品德", "特殊能力/專長",
    "補助/獎學金排斥", "領獎學金後的義務", "獎助金額", "獎助名額", "應繳文件",
    "其他（用於無法歸類的特殊要求）"
]
CONDITION_TYPES = Literal["限於", "包含", "屬性"]


# --- 3. Pydantic 巢狀結構定義 ---

class NumericalAttributes(BaseModel):
    # 用於儲存可計算的數值資訊
    num_value: float = Field(description="核心數值")
    unit: Optional[str] = Field(None, description="單位")
    # 針對成績的額外欄位
    academic_scope: Optional[Literal["學期", "學年", "不適用"]] = Field(None, description="範圍")
    academic_metric: Optional[Literal["百分制", "GPA", "排名", "操行"]] = Field(None, description="評估標準或類型")

class SubTag(BaseModel):
    """描述單一的條件、限制或屬性"""
    tag_category: CATEGORIES = Field(description="標籤大類別")
    condition_type: CONDITION_TYPES = Field(description="條件類型")
    
    # 原始文本 (給人類看)
    tag_value: str = Field(description="原始描述")
    
    # 標準化值 (給前端篩選用)
    standardized_value: Optional[str] = Field(None, description="標準化詞彙")
    
    # 數值資料 (給前端排序/計算用)
    numerical: Optional[NumericalAttributes] = Field(None, description="數值資料")

class ScholarshipGroup(BaseModel):
    """代表獎學金內的一個獨立申請組別或階段。"""
    group_name: str = Field(
        description="組別名稱"
    )
    requirements: List[SubTag] = Field(
        description="此組別的申請條件或屬性"
    )

class FinalTagsStructure(BaseModel):
    # 最終輸出結構：包含所有組別和頂層 common tags
    groups: List[ScholarshipGroup] = Field(
        default_factory=list)
    common_tags: List[SubTag] = Field(
        default_factory=list)


# 最終用於 API 呼叫的 Schema (JSON Schema 格式)
FINAL_SCHEMA_PYDANTIC = FinalTagsStructure.model_json_schema()


# --- 4. Prompt ---
COUNTY_LIST = "臺北市, 新北市, 基隆市, 桃園市, 臺中市, 臺南市, 高雄市, 宜蘭縣, 新竹縣, 苗栗縣, 彰化縣, 南投縣, 雲林縣, 嘉義縣, 屏東縣, 花蓮縣, 臺東縣, 澎湖縣, 金門縣, 連江縣"
COLLEGE_LIST = "文學院, 理學院, 社會科學院, 醫學院, 工學院, 生物資源暨農學院, 管理學院, 公共衛生學院, 電機資訊學院, 法律學院, 生命科學院, 國際政經學院, 國際學院, 創新設計學院, 重點科技研究學院, 共同教育中心, 進修推廣學院"

SYSTEM_PROMPT = f"""
# 系統指令：專業獎學金標籤結構化引擎

你的任務是將獎學金文本轉換為結構化數據，以便支援前端網站的「勾選/篩選」和「數值排序」功能。

**核心目標：**
1. **分組：** 識別獎學金中的所有獨立申請組別。如果只有一個組別，請命名為「通用組別」。
2. **分類：** 將每個組別下的條件，準確歸類到 19 個 `tag_category` 之一。
3. **結構化：** 將 tag_value 轉化為前端可用的數據：
    * **標準化 **：將條件映射到指定的標準選項清單。
    * **數值化**：將成績、金額、名額提取為可計算的數字結構。
4. **歸屬：** 將 group 特有條件放入該組的 `requirements` 列表內。
5. **通用：** 若有 multi groups，將適用於 all groups 的通用條件放入 `common_tags` 列表內。

---

## 標籤大類別 (tag_category)
你必須且只能使用以下 19 個分類作為 "tag_category" 的值：
{', '.join(CATEGORIES.__args__)}

---

## 條件類型邏輯定義 (condition_type)
請根據以下功能性定義，判斷每一項標籤應屬於哪一種類型。

### 規則一：限於 (LimitedTo)
**功能性限制 (強制要求)：** 凡是申請人必須滿足的單一或複合條件，都視為「限於」。
**負面排除原則：** 若原文為「排除/禁止」某特定群體，此條件的本質是限制為「**非該群體**」。`standardized_value` **必須**根據上下文判斷後，映射為「**符合資格**」的身分, ** `tag_value` 保留原文。

### 規則二：包含 (Includes)
**多重、可替代的合格集合 (擇一滿足)：** 多種可替代的合格途徑，滿足集合中任一項即可通過該要求類別。

### 規則三：屬性 (Attribute)
**描述性特徵或義務 (Non-Eligibility)。

---

## 1. 標準化映射規則
若標籤屬於以下類別，必須從清單中選擇最接近的一個值填入 `standardized_value`。若無對應，填「其他」。

* **學制：** 大學, 碩士, 博士, 在職專班, 進修部, 推廣教育, 其他。
* **年級：** 1, 2, 3, 4, 4 以上 (若為範圍，列出所有符合年級，如 "2, 3, 4, 4以上")。
* **學籍狀態：** 在學生, 延畢生, 轉學生, 休學生, 其他。
* **學院：** **必須**從以下學院清單中選擇最相關的**學院名稱**填入：{COLLEGE_LIST}。

* **國籍身分：** 不限, 本國籍, 僑生, 港澳生, 陸生, 外籍生, 其他。
    * *推論規則：*
        1. 提及「中華民國身分證」、「戶籍」、「設籍」、「戶口名簿」，或特殊身分包含「原住民」、「新住民」 $\to$ **本國籍** (含歸化或定居者)。        
        2. 提及「僑生」或「僑委會」 $\to$ **僑生**。
        3. 提及「港澳生」 $\to$ **港澳生**。
        4. 提及「陸生」或「大陸地區學生」 $\to$ **陸生**。
        5. 提及「外籍生」或「國際學生」 $\to$ **外籍生**。
        6. **若全文皆未提及上述任何身分或國籍關鍵字，請根據邏輯判斷，映射為「不限」或「其他」。**
* **設籍地/就讀地：** (填寫以下縣市之一，或填寫「不限」)) {COUNTY_LIST} 
    * *推論規則：* 若原文提及「臺灣地區」、「全國」、「國內」或**未指定**特定縣市，**必須**映射為「**不限**」。   
    * **`tag_value`：** 必須提取原文中最精確的地理限制（區、鄉、里等），用於後端最終檢查。

* **特殊身份：** 原住民, 新住民, 身心障礙, 團體, 其他。
    * 若申請對象非個人，而是學生社團或團體，請映射為「**團體**」。
* **家庭境遇：** 單親, 父母雙亡, 家庭突遭變故, 特殊境遇家庭（證明）,其他。
    * **強制規則：** 若原文包含「雙亡」，必須映射為「父母雙亡」，嚴禁映射為「單親」。
    * *推論規則：* 若原文提及「特殊境遇」或「特境家庭」，**必須**映射為「**特殊境遇家庭（證明）**」。若僅描述「生活發生變故」但未提及特境證明，則映射為「家庭突遭變故」。
* **經濟相關證明：** 低收入戶證明, 中低收入戶證明, 村里長提供之清寒證明, 導師提供之清寒證明, 國稅局家戶所得證明, 其他。
    * *推論規則：* 若資格描述模糊（如「家境清寒」），請**主動參考「應繳文件」區塊**，若有具體文件，請將其映射為該標準值。 
    * 清寒證明若未寫明是由村里長或導師提供，優先映射為**「村里長提供之清寒證明」**。  

* **操行/品德：** 無懲處紀錄, 無申誡以上處分, 無小過以上處分, 無大過以上處分, 其他。
    * *邏輯：* 懲處等級依序為：書面告誡 < 申誡 < 小過 < 大過 < 勒令退學 < 開除學籍。請依據**最嚴格的門檻**選擇。
    * ***抽象的品德特質（如慈悲、熱心）請歸類到「其他」。**

* **補助/獎學金排斥：** 不得兼領, 特定項目不得兼領, 可兼領但有額度上限, 可兼領, 其他。
    * *關鍵邏輯：* * 若說「不得領有**任何**其他獎學金」，映射為「**不得兼領**」。* 若列出「不得領有**以下**獎學金」或「已領有...者不得申請」但允許部分例外(如學雜費減免)，映射為「**特定項目不得兼領**」。

---

## 2. 數值結構化規則 

* **核心學業要求 / 操行/品德：** 填寫 `academic_scope`, `academic_metric` (百分制/GPA/排名/操行) 和 `num_value`。
* **獎助金額：** * 提取金額數值 (`num_value`) 和單位 (`unit`)。`academic_scope` 和 `academic_metric`（必須為 null）。
    * 若金額隨組別不同，請確保將標籤放在正確的 `groups` 內。
* **錄取名額 ：** * 提取名額數值 (`num_value`) 和單位 (`unit`)。`academic_scope` 和 `academic_metric`（必須為 null）。

---

## 3. 其他邏輯

1. **特定條件歸屬：** **僅適用於特定組別**的條件，**嚴禁**放入 `common_tags`。
2. **通用標籤排斥：** 已在 `common_tags` 的條件，不得重複出現在 `groups` 內。
3. **複合條件拆分 (Force Split)：**若原文包含多個獨立選項（A 或 B、A 及 B），**必須**拆分為多個獨立的標籤。
    * **錯誤示範：** `tag_value`: "低收入戶或里長清寒證明" (未拆分)
    * **正確示範：** * Tag 1: `tag_value`: "低收入戶", `standardized_value`: "低收入戶證明"
        * Tag 2: `tag_value`: "里長清寒證明", `standardized_value`: "村里長提供之清寒證明"
4. **證明文件歸類原則 (優先級提升)：** 若某個**應繳文件**具備「證明資格」的功能（包含經濟證明、特殊身分證明、或**家庭境遇證明**），請優先將其歸類為對應的資格類別（即 `經濟相關證明`、`特殊身份` 或 `家庭境遇`），並設定 `condition_type` 為 `包含` 或 `限於`，**嚴禁**將其僅歸類為普通的 `應繳文件`。
5. **排除資訊：** **忽略**申請/截止日期**資訊。
6. **例外處理：** 無法歸類到 1-18 類者，請使用 **第 19 類 (其他)**。


## JSON 輸出格式 (Schema)
你必須且只能輸出一個符合 `FinalTagsStructure` Pydantic 模型的 JSON 物件。
"""

# --- 5. 批次處理設定 ---
INPUT_FILE = os.path.join("data", "processed", "scholarships_with_full_text_for_llm.json")
OUTPUT_DIR = os.path.join("data", "analysis")
ERROR_LOG_FILE = os.path.join("data", "analysis", "error_log.txt")

# --- 6. 批次處理邏輯 ---
def process_single_scholarship(item):
    """處理單筆獎學金，回傳 (success, result/error_message)"""
    s_id = item.get('id')
    full_text = item.get('full_text_for_llm')
    
    if not s_id or not full_text:
        return False, "資料欄位缺失 (缺少 id 或 full_text_for_llm)"

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": "請根據以下資料生成結構化標籤：\n\n### 待標籤的獎學金資料 ###\n" + full_text}]}
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT, 
                response_mime_type="application/json",
                response_schema=FINAL_SCHEMA_PYDANTIC, 
            ),
        )
        
        # 驗證結構
        tags_object = FinalTagsStructure.model_validate_json(response.text)
        
        # 插入 ID 與名稱以便辨識
        result_dict = tags_object.model_dump()
        result_dict["id"] = s_id
        result_dict["name"] = item.get("scholarship_name", item.get("名稱", "未知名稱"))
        
        return True, result_dict

    except ValidationError as e:
        return False, f"Pydantic 驗證失敗: {str(e)}"
    except Exception as e:
        return False, f"API 或其他錯誤: {str(e)}"

def run_batch_processing():
    print(f"--- 開始批次處理 ---")
    print(f"輸入檔案: {INPUT_FILE}")
    print(f"輸出目錄: {OUTPUT_DIR}")
    
    # 1. 確保目錄存在
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 2. 讀取輸入檔
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 錯誤：找不到輸入檔 {INPUT_FILE}")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data_list = json.load(f)
    
    total_count = len(data_list)
    print(f"總共發現 {total_count} 筆資料待處理。")
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    # 3. 迴圈處理
    for index, item in enumerate(data_list):
        s_id = str(item.get('id', 'unknown'))
        output_path = os.path.join(OUTPUT_DIR, f"result_{s_id}.json")
        
        # 斷點續傳檢查：如果檔案已存在，就跳過
        if os.path.exists(output_path):
            print(f"[{index+1}/{total_count}] ID {s_id} 已存在，跳過。")
            skip_count += 1
            continue
            
        print(f"[{index+1}/{total_count}] 正在處理 ID {s_id} ... ", end="", flush=True)
        
        success, result = process_single_scholarship(item)
        
        if success:
            # 寫入成功檔案
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=4, ensure_ascii=False)
            print("✅ 成功")
            success_count += 1
        else:
            # 記錄錯誤
            print(f"❌ 失敗")
            error_msg = f"ID {s_id}: {result}\n"
            with open(ERROR_LOG_FILE, "a", encoding="utf-8") as log:
                log.write(error_msg)
            error_count += 1
        
        # 可選：避免 API Rate Limit
        # import time
        # time.sleep(0.5)

    print("\n--- 處理完成 ---")
    print(f"成功: {success_count}")
    print(f"跳過: {skip_count}")
    print(f"失敗: {error_count}")
    if error_count > 0:
        print(f"詳細錯誤請查看: {ERROR_LOG_FILE}")

if __name__ == "__main__":
    run_batch_processing()
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
        1. 提及「中華民國身分證」、「戶籍」、「設籍」、「戶口名簿」或「原住民」 $\to$ **本國籍** (含歸化或定居者)。        
        2. 提及「僑生」或「僑委會」 $\to$ **僑生**。
        3. 提及「港澳生」 $\to$ **港澳生**。
        4. 提及「陸生」或「大陸地區學生」 $\to$ **陸生**。
        5. 提及「外籍生」或「國際學生」 $\to$ **外籍生**。
        6. **若全文皆未提及上述任何身分或國籍關鍵字，請映射為「不限」。**
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

# --- 5. 測試資料 (使用 ID 6050 的 full_text_for_llm 內容) ---
# 這是您提供的三重東區扶輪社資料，模型需要識別出清寒、成績、冠名三個組別
TEST_DATA_6050 = """
### 獎學金核心元數據 (FOR LLM REFERENCE) ###\n名稱: 彰化縣建大優秀自強獎學金\nID: 6050\n起始日期: 2025/9/30\n截止日期: 2025/10/7\n金額: 新台幣2萬元\n名額: 全國大專院校學生限28名\n申請地點: 申請系統：請在申請截止日下午17點之前，於fao系統登記並繳交全部紙本至生輔組。 https://my.ntu.edu.tw/fao/login.aspx\n\n\n### 網站公告：申請資格 (Eligibility) - 原始文本 ###\n一、有下列任一條件者，不得申請： （一）已享有公費或其他獎學金者，不得申請。 （二）前一學年有一學科不及格者，不得申請。 （三）碩博士班不得申請。 二、符合下列全部條件者，得申請： （一）設籍於彰化縣為一年以上之優秀自強學生 （二） 前一學年之學業成績平均七十分以上(大一學生以高三成績為準) ，操行成績(或綜合表現)八十分(甲等)以上，且綜合表現良好無記過以上之處分。 三、承辦人：林奕延先生， linyiyan@ntu.edu.tw ，02-33662050轉221\n\n\n### 網站公告：應繳文件 (Required Documents) - 原始文本 ###\n紙本資料請投至生輔組1號櫃台「公設獎學金紙箱」如下圖（ 現場備有免費迴紋針及環保紙袋供您使用，保護隱私 ）： 一、 待交文件表（獎學金系統列印） 二、專用申請書 三、6個月內全戶戶籍謄本，需含詳細記事。 （戶籍謄本可於臺北市大安戶政事務所申請，或以自然人憑證線上申請列印） 四、前一學年成績單正本（大一新生附高三成績） 五、學生證正反面影本（需加蓋註冊圓章）或在學證明 六、鄉（鎮、市）公所出具低收、中低收入戶證明正本 七、導師推薦證明。（特境家庭非低收或中低收入戶，應提供此證明）因故無法取得導師簽章者，得由系主任代理。 八、操行成績證明（myntu列印） 九、獎懲紀錄證明（myntu列印）\n\n\n### 附件解析內容 ###\n\n--- 附件 1: 專用申請書及導師推薦函 ---\n建大文化教育基金會114年彰化縣優秀自強學生獎學金申請書\n「學生姓名\n性別\n編號:(\n)申請學校勿填寫\n校名\n就讀學校\n年制\n學制科系\n年級 □日間部 □夜間部申請\n系(科)( 年 月入學)組別\n大專組(含院校)\n身 字\n分證\n出生日期 年月日\n號\n是否享有\n已領受公費待遇或其他獎學金\n前學年成績\n公費待遇 未領受公費待遇或其他獎學金\n學業\n| 戶籍地址 於截止申請日設籍彰化縣已滿1年 未滿1年\n(智育)\n操行(德育)\n依辦法第2條\n連絡電話:\n手機號碼:\n上學期\n連絡方式 Email:\n下學期\n聯絡地址:\n父:\n□ □ 殁 職業:\n母:\n□ □ 殁 職業:\n家庭經濟\n狀況概述\n□ 獎學金申請書。 □ 學生證影本或□在學證明書。\n□ 前一學年學業成績証明書(單)正本。(上、下學期)\n□ 六個月內戶籍謄本正本。(勿附戶口名簿)\n「繳附證件 清寒證明種類:(勿附村里長證明)\n學校審查意見\n(請蓋辦理單位戳章)\n□ 低收入戶證明 □ 中低收入戶證明\n□ 學校證明(由學校證明家境狀況而推薦,學業上或課外活動有特殊\n表現者可納入加分重點)\n[ 申請學生\n簽(蓋)章\n承辦單位及人員(核章)\n聯絡電話:\n審查小組意見(學校勿填)\n學校 學校地址:\n辦理\n校 長\n中華民國\n核章\n校印\n年月\n日\n附註:一 ·本申請書各欄均應逐項詳填,如有遺漏或手續不全則不予審查。\n二、\n、各項手續辦妥後由就讀學校彙轉,個人申請概不受理。\n三、學校審查意見請力求確實,並於審查後於申請書正下處加蓋學校關防(或戳記)\n建大文化教育基金會114年彰化縣優秀自強學生獎學金\n學校推薦函\n學生姓名\n就讀學校\n科系、年級\n學生家庭\n生活情況\n相關說明\n校印\n推薦人簽名:\n推薦人是申請學生的:\n學校辦理單\n位審查意見\n附註:本證明各欄應本行為事實記錄,學業上或課外活動有特殊表現為審查重點。(輔\n以相關資料佐證為佳),學校審查請力求確實,並於審查後於申請書右上角處加\n蓋學校關防(或戳記)。
"""

# --- 6. 執行測試 ---
def run_test():
    print(f"--- 呼叫 Gemini {MODEL_NAME} 進行巢狀標籤提取 (ID 6050) ---")

    try:
        # ！！！ 關鍵改動點 1：將 SYSTEM_PROMPT 移到 system_instruction 參數 ！！！
        response = client.models.generate_content(
            model=MODEL_NAME,
            
            # 關鍵改動點 2：contents 參數現在只包含數據，不包含長指令字串
            contents=[
                {"role": "user", "parts": [{"text": "請根據以下資料生成結構化標籤：\n\n### 待標籤的獎學金資料 ###\n" + TEST_DATA_6050}]}
            ],
            
            config=types.GenerateContentConfig(
                # 這裡使用了 SYSTEM_PROMPT 變數，模型會將其視為高優先級的系統設定
                system_instruction=SYSTEM_PROMPT, 
                response_mime_type="application/json",
                response_schema=FINAL_SCHEMA_PYDANTIC, 
            ),
        )
   
        # 1. 使用 Pydantic 自動驗證模型輸出
        tags_object = FinalTagsStructure.model_validate_json(response.text)
        result_data = tags_object.model_dump() # 保持預設，保留 null

        # 2. 設定存檔路徑
        output_dir = os.path.join("data", "analysis")
        output_file = os.path.join(output_dir, "test_result_6050.json")

        # 3. 確保資料夾存在
        os.makedirs(output_dir, exist_ok=True)

        # 4. 寫入檔案
        print(f"\n正在寫入檔案至: {output_file} ...")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result_data, f, indent=4, ensure_ascii=False)

        print("✅ 存檔成功！")

        # 5. (選擇性) 仍在終端機顯示摘要
        print(f"\n[摘要] 總共提取了 {len(tags_object.groups)} 個獨立組別。")
        if tags_object.common_tags:
             print(f"[摘要] 提取了 {len(tags_object.common_tags)} 個通用條件。")

    except ValidationError as e:
        print(f"\n🚨 Pydantic 驗證失敗：模型輸出的 JSON 結構不符合您的 Pydantic Schema。")
        print(f"錯誤詳情: {e}")
        # 在實際的批次處理中，您需要將 response.text 記錄下來進行人工檢查。
    except types.errors.APIError as e:
        print(f"\nAPI 錯誤：{e}")
        print("請檢查您的 API 金鑰是否有效，或確認 API 服務是否正常。")
    except Exception as e:
        print(f"\n發生錯誤: {e}")

if __name__ == "__main__":
    run_test()
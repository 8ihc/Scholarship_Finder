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


# --- 2. 最終版 17 個類別定義 (用於 Pydantic Literal 限制) ---
CATEGORIES = Literal[
    "學制相關", "年級相關", "學籍狀態", "領域/科系", "設籍地",
    "就讀地", "特殊身份", "家庭境遇",
    "經濟相關證明", "核心學業要求", "操行/品德", "特殊能力/專長",
    "補助/獎學金排斥", "領獎學金後的義務", "金額與名額", "應繳文件",
    "其他（用於無法歸類的特殊要求）"
]
CONDITION_TYPES = Literal["限於", "包含", "屬性"]


# --- 3. Pydantic 巢狀結構定義 ---

class NumericalAttributes(BaseModel):
    """用於儲存核心學業要求、操行成績、獎學金金額、名額等可計算的數值資訊。"""
    num_value: float = Field(description="核心數值 (例如：75, 20000, 3)。")
    unit: Optional[str] = Field(None, description="單位 (例如：分, 元, 名)。")
    # 針對成績的額外欄位
    academic_scope: Optional[Literal["學期", "學年", "不適用"]] = Field(None, description="成績要求範圍：學期、學年。")
    academic_metric: Optional[Literal["分數", "百分制", "GPA", "排名", "操行"]] = Field(None, description="評估標準或類型：分數、百分制、GPA、排名、操行。")

class SubTag(BaseModel):
    """描述單一的條件、限制或屬性，升級以支援結構化篩選。"""
    tag_category: CATEGORIES = Field(description="標籤大類別。")
    condition_type: CONDITION_TYPES = Field(description="條件類型：限於（限制）、包含（OR集合）、屬性（描述）。")
    
    # 原始文本 (給人類看)
    tag_value: str = Field(description="從原文提取的完整描述，若資訊依賴於子條件(如金額隨學制變)，必須在內容中註明其依賴的條件。")
    
    # 關鍵新增：標準化值 (給勾選框用)
    standardized_value: Optional[str] = Field(
        None, 
        description="將 tag_value 轉為標準化清單中選出的標準詞彙。若該類別尚未標準化 (如特殊能力)，則為 None。"
    )
    
    # 關鍵新增：數值資料 (給排序/計算用)
    numerical: Optional[NumericalAttributes] = Field(
        None, 
        description="若標籤包含分數、金額或名額，必須填寫此物件。"
    )

class ScholarshipGroup(BaseModel):
    """代表獎學金內的一個獨立申請組別或階段。"""
    group_name: str = Field(
        description="此組別或階段的名稱。如果獎學金只有一個組別，請命名為「通用組別」。"
    )
    requirements: List[SubTag] = Field(
        description="此組別下所有獨立的申請條件、限制、金額和文件要求清單。"
    )

class FinalTagsStructure(BaseModel):
    """最終輸出結構：包含所有組別和頂層共同條件。"""
    groups: List[ScholarshipGroup] = Field(
        default_factory=list,
        description="獎學金內所有獨立的申請組別清單。"
    )
    common_tags: List[SubTag] = Field(
        default_factory=list,
        description="適用於整個獎學金的通用條件。"
    )


# 最終用於 API 呼叫的 Schema (JSON Schema 格式)
FINAL_SCHEMA_PYDANTIC = FinalTagsStructure.model_json_schema()


# --- 4. Prompt ---
COUNTY_LIST = "臺北市, 新北市, 基隆市, 桃園市, 臺中市, 臺南市, 高雄市, 宜蘭縣, 新竹縣, 苗栗縣, 彰化縣, 南投縣, 雲林縣, 嘉義縣, 屏東縣, 花蓮縣, 臺東縣, 澎湖縣, 金門縣, 連江縣"
COLLEGE_LIST = "文學院, 理學院, 社會科學院, 醫學院, 工學院, 生物資源暨農學院, 管理學院, 公共衛生學院, 電機資訊學院, 法律學院, 生命科學院, 國際政經學院, 國際學院, 創新設計學院, 重點科技研究學院, 共同教育中心, 進修推廣學院"

SYSTEM_PROMPT = f"""
# 系統指令：專業獎學金標籤結構化引擎

你的任務是將獎學金文本轉換為結構化數據，以便支援前端網站的「勾選/篩選」和「數值排序」功能。請將數據分為三個層次：原始描述 (tag_value)、標準化勾選值 (standardized_value) 和數值 (numerical)。

**核心目標：**
1. **分組：** 識別獎學金中的所有獨立申請組別。如果只有一個組別，請命名為「通用組別」。
2. **分類：** 將每個組別下的條件，準確歸類到 17 個 `tag_category` 之一。
3. **結構化：** 將 tag_value 轉化為前端可用的數據：
    * **標準化 (`standardized_value`)**：將條件映射到指定的標準選項清單（用於勾選）。
    * **數值化 (`numerical`)**：將成績、金額、名額提取為可計算的數字結構（用於排序）。
4. **歸屬：** 將組別特有的條件放入該組的 `requirements` 列表內。
5. **通用：** 將適用於整個獎學金的通用條件放入 `common_tags` 列表內。

---

## 標籤大類別 (tag_category)
你必須且只能使用以下 17 個分類作為 "tag_category" 的值：
{', '.join(CATEGORIES.__args__)}

---

## 條件類型邏輯定義 (condition_type)
你只能使用 **「限於」**、**「包含」** 或 **「屬性」**。請根據以下功能性定義，判斷每一項標籤應屬於哪一種類型。

### 規則一：限於 (LimitedTo)
**功能性限制 (AND/強制要求)：** 凡是申請人必須滿足的單一或複合條件，都視為「限於」。

### 規則二：包含 (Includes)
**多重、可替代的合格集合 (OR/擇一滿足)：** 僅用於描述多種獨立、可替代的合格途徑，表示滿足集合中任一項即可通過該要求類別。

### 規則三：屬性 (Attribute)
**描述性特徵或義務 (Non-Eligibility)：** 適用於描述獎學金的量化資訊或申請人必須履行的義務等。

---

## 1. 標準化映射規則 (填寫 standardized_value)
若標籤屬於以下類別，必須從清單中選擇最接近的一個值填入 `standardized_value`。若無對應，填「其他」。

* **學制相關：** 大學, 碩士, 博士, 在職專班, 進修部, 推廣教育, 其他
* **年級相關：** 1, 2, 3, 4, 4以上
* **學籍狀態：** 在學生, 延畢生, 轉學生, 休學生, 其他
* **家庭境遇：** 單親, 父母雙亡, 家庭突遭變故, 其他
* **設籍地/就讀地：** (填寫以下縣市之一) {COUNTY_LIST}
    * **`tag_value`：** 必須提取原文中最精確的地理限制（區、鄉、里等），用於後端最終檢查。
    * **`standardized_value`：** 僅填寫對應的**縣市名稱**，用於前端勾選。
* **領域/科系：** **必須**從以下學院清單中選擇最相關的**學院名稱**填入：{COLLEGE_LIST}。
* **特殊身份：** 原住民, 僑生, 陸生, 身心障礙, 其他
* **經濟相關證明：** 低收入戶證明, 中低收入戶證明, 村里長提供之清寒證明, 導師提供之清寒證明, 國稅局家戶所得證明, 其他
* **補助/獎學金排斥：** 不得兼領, 可兼領, 可兼領但有額度上限

**本次運行排除標準化**
* **特殊能力/專長 與 領獎學金後的義務：** 在本次運行中，請勿填寫 `standardized_value` 欄位。

---

## 2. 數值結構化規則 (填寫 numerical)
若標籤包含分數、金額或名額，必須填寫 `numerical` 物件。

* **核心學業要求 / 操行/品德：** 必須填寫 `academic_scope` (學期/學年)、`academic_metric` (分數/百分制/GPA/排名/操行) 和 `num_value`。
* **金額與名額：** 必須將金額和名額分成**兩個獨立的標籤**，並在各自的 `numerical` 物件中填寫 `num_value` 和 `unit`。

---

## 3. 其他規則

1.  **特定條件歸屬：** 任何**僅適用於特定組別**的條件，必須放在該組別的 `requirements` 內，**嚴禁**放入 `common_tags`。
2.  **通用標籤排斥：** 如果某個條件已存在於 `common_tags` 中，則不得重複出現在任何 `groups` 內。
3.  **複合條件拆分**： 嚴禁將多個可標準化的值合併在同一個 tag_value 中（例如：「低收或身障」需拆成兩個標籤;「家境清寒且父母雙亡」需拆成兩個標籤），以確保每個標籤都能對應單一的 standardized_value。
4.  **應繳文件：** 必須列出所有明確要求繳交的**實質性文件名稱**。
5.  **排除資訊：** 請**忽略並排除**申請/截止日期**資訊。
6.  **例外處理：** 無法歸類到 1-16 類的特殊要求，請使用 **第 17 類 (其他)**。


## JSON 輸出格式 (Schema)
你必須且只能輸出一個符合 `FinalTagsStructure` Pydantic 模型的 JSON 物件。
"""

# --- 5. 測試資料 (使用 ID 7897 的 full_text_for_llm 內容) ---
# 這是您提供的三重東區扶輪社資料，模型需要識別出清寒、成績、冠名三個組別
TEST_DATA_7897 = """
### 獎學金核心元數據 (FOR LLM REFERENCE) ###\n名稱: 114學年度『三重東區扶輪社獎助學金』\nID: 7897\n起始日期: 2025/12/3\n截止日期: 2026/2/5\n金額: 20000\n名額: 6名\n申請地點: 申請系統 本校學生財務支援服務系統 https://my.ntu.edu.tw/fao/login.aspx\n\n\n### 網站公告：申請資格 (Eligibility) - 原始文本 ###\n限設籍在三重、蘆洲、新莊、五股、泰山、八里、林口等7區在學大學生； 曾得過該社獎學金者請勿再申請 ， 若重複申請指定地區之其他扶輪社獎學金，即取消獲獎資格。 （一）清寒優良獎學金 ： 1、大學部大二以上在學學生。 2、父母雙亡、貧戶證明或家境清寒，且在民國112年7月1日前已設籍於指定區域者。 3 、 113學年操行80分以上、學業成績平均75分以上，且未受記過以上處分者。 ( 附獎懲紀錄證明 ) 4 、 113學年度內，經學校證明未領有其他獎學金及公費者 。 （二）成績優良獎學金 1 、 大學部在學學生。 2 、 民國112年7月1日前已設戶籍指定區域者。 3 、 113學年操行及學業成績平均80分以上，且未受記過以上處分者( 附獎懲紀錄證明 )。 4 、 113學年度內，經學校證明未領有其他獎學金者。 （三）冠名獎學金 ： 1 、 大學部在學學生。 2 、 民國112年7月1日前已設戶籍於三重區者。 3 、 113學年操行及學業成績平均80分以上，且未受記過以上處分者( 附獎懲紀錄證明 )。 4 、 113學年度內，經學校證明未領有其他獎學金者 。 ★注意：「113學年度內未領取其他獎助學金」，如有領取其他獎助學金又未告知設獎單位者，則依規定取消獲獎資格並列入本組紀錄。\n\n\n### 網站公告：應繳文件 (Required Documents) - 原始文本 ###\n★本獎學金請注意截止時間為2/5（四）下午5時止，逾期不予受理。 （一）待繳文件列表-登入系統填寫送出列印 （二）該會專用申請書（ 請填寫1份即可，並貼照片；推薦人請找所屬科系系主任，本組不予核蓋推薦單位與推薦人 ）。 （三）在學證明正本 （四） 歷年成績單正本、操行與獎懲證明、113學年度名次證明正本。 （五） 全家人 新式戶口名簿正本（需含記事） （勿附舊式戶口名簿影本）。 （六） 申請 「清寒獎學金」請務必附上政府低收或里長清寒證明，申請其他兩類不用附。 （七）113學年度未領其他獎學金之證明書，收件後統一由本組核章。 （八）「自傳及未來理想」，限用電腦打字（800字以內）。 （九）文章1篇─我對扶輪社的認知，限用電腦打字（2千字以上）。\n\n\n### 附件解析內容 ###\n\n--- 附件 1: 辦法及專用申請書 ---\nROTARY\nERNA\nTONAL\n三重東區扶輪社\nRotary Club Of Sanchung East\n獎助學金實施細則\n宗旨:\n鼓勵與資助本社轄區及鄰近地區(共計三重、蘆洲、新莊、五股、泰山、八里、林口共七區)在校成績優良及\n清寒優秀大學生而設。\n二、獎助學金之種類:\n(一)清寒優良獎學金 (二)成績優良獎學金 (三)冠名獎學金\n三、申請資格:\n(一)清寒優良獎學金\n1、現為公私立大專院校在校學生及五專五年級生(不包含研究所)。\n2、父母雙亡或貧戶證明或家境清寒,且在民國一一二年七月一日前已設籍於上述七區內。\n3、前學年(上、下學期)操行甲等、學業成績平均七十五分以上,且未受記過以上處分者。\n4、一一三學年度內,經學校證明未領有其他獎學金者。(領取行政院減免學雜費案者扔可申請)\n5、公費生不得申請。\n6、曾得過本社獎學金者請勿再申請。\n7、若重複申請上述七區內之其他扶輪社獎學金,即取消獲獎資格。\n(二)成績優良獎學金\n1、現為公私立大專院校在校學生(不包含研究所)。\n2、民國一一二年七月一日前已設戶籍於上述七區內者。\n3、前學年(上、下學期)操行甲等、學業成績平均八十分以上,且未受記過以上處分者。\n4、一一三學年度內,經學校證明未領有其他獎學金者。(領取行政院減免學雜費案者可申請)\n5、曾得過本社獎學金者請勿再申請。\n6、若重複申請上述七區之其他扶輪社獎學金,即取消獲獎資格。\n(三)冠名獎學金\n1、現為公私立大專院校在校學生(不包含研究所)。\n2、民國一一二年七月一日前已設戶籍於上述七區者。\n3、前學年(上、下學期)操行甲等、學業成績平均八十分以上,且未受記過以上處分者。\n4、一一三學年度內,經學校證明未領有其他獎學金者。(領取行政院減免學雜費案者扔可申請)\n5、曾得過本社獎學金者請勿再申請。\n6、若重複申請上述七區之其他扶輪社獎學金,即取消獲獎資格。\n四、名額及獎助金額:\n1、名額: 3 名。\n2、金額:每名新台幣貳萬元。\n五、申請日期:即日起迄至民國115年2月28日止。\n六、評審:經本社獎學金委員會初審,可能面談,再經理事會複審,於民國115年3/25前通知錄取\n者,未錄取者不另行通知,本社可依實際報名人數做適度的名額與相關辦法調整。\n七、獎助給付:於本社紀念慶典中頒發(可授權代領),時間、地點另行通知。\n八、申請手續:填具申請書二份,連同有關證明文件於規定日期前以掛號信寄交本社(以郵戳為憑)。\n備註:\n1、應繳附文件:\n(1)在學證明文件(研究所、進修推廣部除外)。\n(2)前學年(上、下學期)學業成績單及操行證明單乙份(需有體育成績)。\n(3)當月全戶戶籍謄本(請至戶政事務所申請,勿附戶口名簿)。\n(4)低收入戶或貧戶證明或里長之家境清寒證明乙份。\n(5)該年度未領其他獎學金之證明書。(領取行政院減免學雜費案者扔可申請)\n(6)自傳及未來理想,限用電腦打字(800字以內)\n(7)文章一篇--我對扶輪社的認知,限用電腦打字(2千字以上)。\n2、請填寫二份,於民國115年2月28日前一份寄交本社,一份由推薦單位存查。\n3、本申請書不夠時,請自行影印。或以e-mail:3490scerc@gmail.com 主旨:索取獎學金申請書電子檔\n郵寄地址:241 三重正義郵局第 00068 號郵政信箱 林主委世堂先生收 聯絡電話:(02)2988-8925 呂小姐\nRotary\nClub of Sanchung East"
"""

# --- 6. 執行測試 ---
def run_test():
    print(f"--- 呼叫 Gemini {MODEL_NAME} 進行巢狀標籤提取 (ID 7897) ---")

    try:
        # ！！！ 關鍵改動點 1：將 SYSTEM_PROMPT 移到 system_instruction 參數 ！！！
        response = client.models.generate_content(
            model=MODEL_NAME,
            
            # 關鍵改動點 2：contents 參數現在只包含數據，不包含長指令字串
            contents=[
                {"role": "user", "parts": [{"text": "請根據以下資料生成結構化標籤：\n\n### 待標籤的獎學金資料 ###\n" + TEST_DATA_7897}]}
            ],
            
            config=types.GenerateContentConfig(
                # 這裡使用了 SYSTEM_PROMPT 變數，模型會將其視為高優先級的系統設定
                system_instruction=SYSTEM_PROMPT, 
                response_mime_type="application/json",
                response_schema=FINAL_SCHEMA_PYDANTIC, 
            ),
        )
        
        # 核心優勢：使用 Pydantic 自動驗證模型輸出
        tags_object = FinalTagsStructure.model_validate_json(response.text)
        
        print("\n--- 標籤提取成功，Pydantic 驗證通過 ---")
        print("--- 解析後的巢狀標籤列表 ---")
        
        # 輸出美化後的 JSON
        print(json.dumps(tags_object.model_dump(), indent=4, ensure_ascii=False))
        
        # 額外提示：確認組別數量
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
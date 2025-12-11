# ========== Numeric Extraction Helper ==========
def extract_numeric_info_from_tags(tags: dict, category: str):
    """
    從 common_tags 和 groups 內 requirements 挖出指定 category (如 獎助金額/獎助名額) 的 AI 數值與原文。
    回傳 (num_value+unit, 原文tag_value)，若多個以第一個為主。
    """
    # 先查 common_tags
    for req in tags.get("common_tags", []):
        if req.get("tag_category") == category:
            numerical = req.get("numerical")
            if numerical and numerical.get("num_value") is not None:
                num_val = numerical.get("num_value")
                unit = numerical.get("unit", "")
                tag_value = req.get("tag_value", "")
                return f"{num_val}{unit}", tag_value
    # 再查 groups
    for group in tags.get("groups", []):
        for req in group.get("requirements", []):
            if req.get("tag_category") == category:
                numerical = req.get("numerical")
                if numerical and numerical.get("num_value") is not None:
                    num_val = numerical.get("num_value")
                    unit = numerical.get("unit", "")
                    tag_value = req.get("tag_value", "")
                    return f"{num_val}{unit}", tag_value
    return None, None
import streamlit as st
import json
import pandas as pd
from typing import List, Dict, Any, Set

# ==================== Page Config ====================
st.set_page_config(
    page_title="NTU Scholarship Finder",
    layout="wide"
)

# ==================== Custom CSS Styling ====================
st.markdown("""
<style>
    /* Global background */
    .stApp {
        background-color: #F2F2EC;
    }
    
    /* Main content area background */
    .main {
        background-color: #F2F2EC;
    }
    
    /* Header area background */
    header[data-testid="stHeader"] {
        background-color: #F2F2EC !important;
    }
    
    /* Toolbar background */
    [data-testid="stToolbar"] {
        background-color: #F2F2EC !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #F1F2EF;
        border-right: none;
        box-shadow: 2px 0 8px rgba(89, 76, 59, 0.1);
    }
    
    /* Sidebar text colors */
    [data-testid="stSidebar"] * {
        color: #594C3B !important;
    }
    
    /* Sidebar headers */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #594C3B !important;
        font-weight: bold;
    }
    
    /* Sidebar labels */
    [data-testid="stSidebar"] label {
        color: #594C3B !important;
        font-weight: 500;
    }
    
    /* Sidebar input fields (selectbox, multiselect, text_input) */
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] input {
        background-color: #E3E2DE !important;
        border: none !important;
        color: #594C3B !important;
    }
    
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="input"] > div {
        background-color: #E3E2DE !important;
        border: none !important;
        color: #594C3B !important;
    }
    
    /* Text input specific styling */
    [data-testid="stSidebar"] input[type="text"] {
        color: #594C3B !important;
        -webkit-text-fill-color: #594C3B !important;
    }
    
    /* Placeholder text color */
    [data-testid="stSidebar"] input::placeholder {
        color: #8B7E6F !important;
        opacity: 0.7;
    }
    
    /* Input text color */
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] [data-baseweb="input"] span {
        color: #594C3B !important;
    }
    
    /* Multiselect & selectbox dropdown popover background (sidebar & main) */
    [data-baseweb="popover"],
    [data-baseweb="popover"] ul,
    [data-baseweb="popover"] li {
        background-color: white !important;
        color: #594C3B !important;
    }
    [data-baseweb="popover"] li:hover {
        background-color: #E3E2DE !important;
    }
    
    /* Selected tag/chip styling for multiselect */
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background-color: #D9B91A !important;
        color: #594C3B !important;
    }
    
    [data-testid="stSidebar"] [data-baseweb="tag"] span {
        color: #594C3B !important;
    }
    
    /* Remove focus borders */
    [data-testid="stSidebar"] [data-baseweb="select"]:focus,
    [data-testid="stSidebar"] [data-baseweb="input"]:focus,
    [data-testid="stSidebar"] input:focus {
        border: none !important;
        outline: none !important;
    }
    
    /* All text colors */
    body, p, span, div, label, h1, h2, h3, h4, h5, h6 {
        color: #594C3B !important;
    }
    
    /* Main title */
    h1 {
        color: #594C3B !important;
        border-bottom: 3px solid #D9B91A;
        padding-bottom: 10px;
    }
    
    /* Subtitle */
    h3 {
        color: #594C3B !important;
    }
    
    /* Section headers in cards */
    .element-container h3,
    .element-container h4 {
        color: #594C3B !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: #594C3B !important;
    }
    
    .stMarkdown * {
        color: #594C3B !important;
    }
    
    /* Expander header styling */
    [data-testid="stExpander"] {
        background-color: white;
        border: none;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    
    [data-testid="stExpander"] summary {
        background-color: #D9B91A;
        color: #594C3B !important;
        font-weight: bold;
        padding: 1rem;
        border-radius: 6px;
    }
    
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span,
    [data-testid="stExpander"] div {
        color: #594C3B !important;
    }
    
    [data-testid="stExpander"] summary:hover {
        background-color: #D9A918;
    }
    
    /* DataFrame styling */
    [data-testid="stDataFrame"] {
        border: none;
    }
    
    /* Info boxes */
    .stInfo {
        background-color: #F2F2EC;
        border-left: none;
    }
    
    /* Warning boxes */
    .stWarning {
        background-color: #FFF9E6;
        border-left: none;
    }
    /* Buttons */
    .stButton > button {
        background-color: #5B7329;
        color: #F2F2EC !important;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background-color: #6D8A35;
        color: white !important;
    }
    
    /* Link buttons */
    .stLinkButton > a {
        background-color: #D9B91A;
        color: #594C3B !important;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        text-decoration: none;
    }
    
    .stLinkButton > a:hover {
        background-color: #D9A918;
        color: #594C3B !important;
    }
    
    /* Checkbox */
    [data-testid="stCheckbox"] label {
        color: #594C3B !important;
    }
    
    /* Metrics and stats */
    [data-testid="stMetricValue"] {
        color: #594C3B !important;
    }
    
    /* DataFrame background */
    [data-testid="stDataFrame"] > div {
        background-color: #F1F2EF !important;
    }
    
    [data-testid="stDataFrame"] table {
        background-color: #F1F2EF !important;
    }
    
    [data-testid="stDataFrame"] thead th {
        background-color: #F1F2EF !important;
        color: #594C3B !important;
        font-weight: bold;
    }
    
    [data-testid="stDataFrame"] tbody tr {
        background-color: #F1F2EF !important;
    }
    
    [data-testid="stDataFrame"] tbody td {
        background-color: #F1F2EF !important;
        color: #594C3B !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background-color: #E3E2DE !important;
    }
    
    /* Additional dataframe styling for dark cells */
    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #F1F2EF !important;
        color: #594C3B !important;
    }
    
    /* DataFrame background */
    [data-testid="stDataFrame"] > div {
        background-color: #F1F2EF !important;
    }
    
    [data-testid="stDataFrame"] table {
        background-color: #F1F2EF !important;
    }
    
    [data-testid="stDataFrame"] thead th {
        background-color: #F1F2EF !important;
        color: #594C3B !important;
        font-weight: bold;
    }
    
    [data-testid="stDataFrame"] tbody tr {
        background-color: #F1F2EF !important;
    }
    
    [data-testid="stDataFrame"] tbody td {
        background-color: #F1F2EF !important;
        color: #594C3B !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background-color: #E3E2DE !important;
    }
    
    /* Additional dataframe styling for dark cells */
    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataFrame"] [role="columnheader"] {
        background-color: #F1F2EF !important;
        color: #594C3B !important;
    }

        /* Custom tooltip for requirements (scoped, safe) */
        .custom-tooltip { position: relative; display: inline-block; }
        .custom-tooltip-value {
            border-bottom: 2.5px dotted #D9B91A;
            cursor: help;
            color: #5B7329;
            font-size: 1rem;
            padding: 0 2px;
        }
        .custom-tooltip-text {
            visibility: hidden;
            min-width: 120px;
            max-width: 350px;
            background: #D9B91A;
            color: #594C3B;
            text-align: left;
            border-radius: 10px;
            padding: 14px 22px;
            position: absolute;
            z-index: 9999;
            bottom: 130%;
            left: 50%;
            transform: translateX(-50%);
            font-size: 1rem;
            font-weight: 500;
            box-shadow: 0 4px 16px rgba(89,76,59,0.12);
            opacity: 0;
            transition: opacity 0.18s;
            pointer-events: none;
            white-space: pre-line;
        }
        .custom-tooltip:hover .custom-tooltip-text {
            visibility: visible;
            opacity: 1;
            pointer-events: auto;
        }
</style>
""", unsafe_allow_html=True)

# ==================== Load Data ====================
@st.cache_data
def load_scholarships():
    with open('data/merged/scholarships_merged_300.json', 'r', encoding='utf-8') as f:
        return json.load(f)

# ==================== Filter Options Based on SYSTEM_PROMPT ====================
FILTER_OPTIONS = {
    "學制": ["大學", "碩士", "博士", "在職專班", "進修部", "推廣教育", "其他"],
    "年級": ["1", "2", "3", "4", "4以上"],
    "學籍狀態": ["在學生", "延畢生", "轉學生", "休學生", "其他"],
    "學院": [
        "文學院", "理學院", "社會科學院", "醫學院", "工學院", 
        "生物資源暨農學院", "管理學院", "公共衛生學院", "電機資訊學院", 
        "法律學院", "生命科學院", "國際政經學院", "國際學院", 
        "創新設計學院", "重點科技研究學院", "共同教育中心", "進修推廣學院"
    ],
    "國籍身分": ["不限", "本國籍", "僑生", "港澳生", "陸生", "外籍生", "其他"],
    "設籍地": [
        "不限", "臺北市", "新北市", "基隆市", "桃園市", "臺中市", 
        "臺南市", "高雄市", "宜蘭縣", "新竹縣", "苗栗縣", 
        "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", 
        "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
    ],
    "就讀地": [
        "不限", "臺北市", "新北市", "基隆市", "桃園市", "臺中市", 
        "臺南市", "高雄市", "宜蘭縣", "新竹縣", "苗栗縣", 
        "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", 
        "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"
    ],
    "特殊身份": ["原住民", "新住民", "身心障礙", "團體", "其他"],
    "家庭境遇": ["單親", "父母雙亡", "家庭突遭變故", "特殊境遇家庭（證明）", "其他"],
    "經濟相關證明": [
        "低收入戶證明", "中低收入戶證明", "村里長提供之清寒證明", 
        "導師提供之清寒證明", "國稅局家戶所得證明", "其他"
    ],
    "操行/品德": [
        "無懲處紀錄", "無申誡以上處分", "無小過以上處分", 
        "無大過以上處分", "其他"
    ],
    "補助/獎學金排斥": [
        "不得兼領", "特定項目不得兼領", "可兼領但有額度上限", 
        "可兼領", "其他"
    ]
}

# ==================== Helper Functions ====================
def extract_tags_from_group(group: Dict, category: str) -> List[str]:
    """Extract standardized_value from a group's requirements by category."""
    values = []
    for req in group.get("requirements", []):
        if req.get("tag_category") == category:
            std_val = req.get("standardized_value")
            if std_val:
                # Handle comma-separated values (e.g., "2, 3, 4, 4以上")
                if "," in std_val:
                    values.extend([v.strip() for v in std_val.split(",")])
                else:
                    values.append(std_val)
    return values

def check_identity_match(group_tags: List[str], user_identities: List[str]) -> bool:
    """
    Check if user's identity matches the group requirement.
    Logic based on condition_type:
    - 限於 (LimitedTo): User must have at least one matching identity
    - 包含 (Includes): User can have any of the listed identities
    - Special case: If group has "不限", it always passes
    """
    if not group_tags:
        return True  # No requirement = pass
    
    group_set = set(group_tags)
    user_set = set(user_identities)
    
    # If "不限" in group tags, always pass
    if "不限" in group_set:
        return True
    
    # Check intersection
    return bool(group_set & user_set)

def check_special_status_match(group_tags: List[str], user_statuses: List[str]) -> bool:
    """
    Check if user's special status meets requirement.
    Uses intersection logic - user must have the required status.
    """
    if not group_tags:
        return True  # No requirement = pass
    
    group_set = set(group_tags)
    user_set = set(user_statuses)
    
    # User must have at least one required status
    return bool(group_set & user_set)

def check_economic_proof_match(group_tags: List[str], user_proofs: List[str]) -> bool:
    """Check if user has required economic proof."""
    if not group_tags:
        return True
    
    group_set = set(group_tags)
    user_set = set(user_proofs)
    
    return bool(group_set & user_set)

def check_group_match(group: Dict, filters: Dict) -> bool:
    """
    Check if a single group matches user's filter criteria.
    A group matches if ALL checked criteria are satisfied.
    """
    # Check 學制
    if filters.get("學制"):
        group_degrees = extract_tags_from_group(group, "學制")
        if group_degrees and not any(d in group_degrees for d in filters["學制"]):
            return False
    
    # Check 年級
    if filters.get("年級"):
        group_grades = extract_tags_from_group(group, "年級")
        if group_grades and filters["年級"] not in group_grades:
            return False
    
    # Check 學籍狀態
    if filters.get("學籍狀態"):
        group_status = extract_tags_from_group(group, "學籍狀態")
        if group_status and not any(s in group_status for s in filters["學籍狀態"]):
            return False
    
    # Check 學院
    if filters.get("學院"):
        group_colleges = extract_tags_from_group(group, "學院")
        if group_colleges and not any(c in group_colleges for c in filters["學院"]):
            return False
    
    # Check 國籍身分 (Special logic)
    if filters.get("國籍身分"):
        group_identities = extract_tags_from_group(group, "國籍身分")
        if not check_identity_match(group_identities, filters["國籍身分"]):
            return False
    
    # Check 設籍地
    if filters.get("設籍地") and filters["設籍地"] != "不限":
        group_domicile = extract_tags_from_group(group, "設籍地")
        if group_domicile and "不限" not in group_domicile and filters["設籍地"] not in group_domicile:
            return False
    
    # Check 就讀地
    if filters.get("就讀地") and filters["就讀地"] != "不限":
        group_study_loc = extract_tags_from_group(group, "就讀地")
        if group_study_loc and "不限" not in group_study_loc and filters["就讀地"] not in group_study_loc:
            return False
    
    # Check 特殊身份
    if filters.get("特殊身份"):
        group_special = extract_tags_from_group(group, "特殊身份")
        if not check_special_status_match(group_special, filters["特殊身份"]):
            return False
    
    # Check 家庭境遇
    if filters.get("家庭境遇"):
        group_family = extract_tags_from_group(group, "家庭境遇")
        if not check_special_status_match(group_family, filters["家庭境遇"]):
            return False
    
    # Check 經濟相關證明
    if filters.get("經濟相關證明"):
        group_economic = extract_tags_from_group(group, "經濟相關證明")
        if not check_economic_proof_match(group_economic, filters["經濟相關證明"]):
            return False
    
    return True

def check_scholarship_match(scholarship: Dict, filters: Dict) -> bool:
    """
    Check if scholarship matches user criteria.
    Returns True if ANY group matches (OR logic across groups).
    """
    # Keyword search
    if filters.get("keyword"):
        keyword = filters["keyword"].lower()
        searchable_text = f"{scholarship.get('scholarship_name', '')} {scholarship.get('eligibility', '')}".lower()
        if keyword not in searchable_text:
            return False
    
    # Check groups
    groups = scholarship.get("tags", {}).get("groups", [])
    common_tags = scholarship.get("tags", {}).get("common_tags", [])
    
    # If no groups, check common_tags only
    if not groups:
        # Create a pseudo-group from common_tags
        pseudo_group = {"requirements": common_tags}
        return check_group_match(pseudo_group, filters)
    
    # Check if ANY group matches
    for group in groups:
        # Combine group requirements with common_tags
        combined_group = {
            "requirements": group.get("requirements", []) + common_tags
        }
        if check_group_match(combined_group, filters):
            return True
    
    return False

def get_requirements_df(group: Dict, exclude_categories: List[str] = None) -> pd.DataFrame:
    """
    Convert group requirements to DataFrame for display.
    Excludes specified categories.
    """
    if exclude_categories is None:
        exclude_categories = ["應繳文件", "領獎學金後的義務", "其他（用於無法歸類的特殊要求）", "獎助金額", "獎助名額"]
    
    requirements = group.get("requirements", [])
    filtered_reqs = [
        req for req in requirements 
        if req.get("tag_category") not in exclude_categories
    ]
    
    if not filtered_reqs:
        return None
    
    data = []
    for req in filtered_reqs:
        row = {
            "類別": req.get("tag_category", ""),
            "條件類型": req.get("condition_type", ""),
            "描述": req.get("tag_value", ""),
            "標準值": req.get("standardized_value", "—")
        }
        
        # Add numerical info if present
        numerical = req.get("numerical")
        if numerical:
            num_val = numerical.get("num_value")
            unit = numerical.get("unit", "")
            if num_val is not None:
                row["數值"] = f"{num_val}{unit}"
            
            scope = numerical.get("academic_scope")
            metric = numerical.get("academic_metric")
            if scope:
                row["範圍"] = scope
            if metric:
                row["評估標準"] = metric
        
        data.append(row)
    
    return pd.DataFrame(data)

def extract_documents_from_group(group: Dict) -> List[str]:
    """Extract document requirements from group."""
    docs = []
    for req in group.get("requirements", []):
        if req.get("tag_category") == "應繳文件":
            docs.append(req.get("tag_value", ""))
    return docs

def extract_obligations_from_group(group: Dict) -> List[str]:
    """Extract obligations from group."""
    obligations = []
    for req in group.get("requirements", []):
        if req.get("tag_category") == "領獎學金後的義務":
            obligations.append(req.get("tag_value", ""))
    return obligations

# ==================== Streamlit App ====================
def main():
    st.title("NTU Scholarship Finder")
    st.markdown("### 基於 AI 標籤的智慧篩選與比對工具")
    
    # Load data
    scholarships = load_scholarships()
    
    # ==================== Sidebar Filters ====================
    st.sidebar.header("篩選條件")
    filters = {}
    # 1. 關鍵字
    filters["keyword"] = st.sidebar.text_input("", placeholder="輸入欲查詢之關鍵字")
    st.sidebar.markdown("---")
    # 2. 數值型欄位
    filters["獎助金額"] = st.sidebar.slider("獎助金額 (元)", min_value=0, max_value=100000, value=(0, 100000), step=1000)
    filters["獎助名額"] = st.sidebar.slider("獎助名額 (人)", min_value=0, max_value=100, value=(0, 100), step=1)
    # 3. 補助/獎學金排斥
    filters["補助/獎學金排斥"] = st.sidebar.multiselect(
        "補助/獎學金排斥",
        options=FILTER_OPTIONS["補助/獎學金排斥"]
    )
    st.sidebar.markdown("---")
    # 4. 學制
    filters["學制"] = st.sidebar.multiselect(
        "學制",
        options=FILTER_OPTIONS["學制"],
        default=["大學"]
    )
    # 5. 年級
    filters["年級"] = st.sidebar.multiselect(
        "年級",
        options=FILTER_OPTIONS["年級"]
    )
    # 6. 學籍狀態
    filters["學籍狀態"] = st.sidebar.multiselect(
        "學籍狀態",
        options=FILTER_OPTIONS["學籍狀態"]
    )
    # 7. 學院
    filters["學院"] = st.sidebar.multiselect(
        "學院",
        options=FILTER_OPTIONS["學院"]
    )
    # 8. 國籍身分
    filters["國籍身分"] = st.sidebar.multiselect(
        "國籍身分",
        options=FILTER_OPTIONS["國籍身分"],
        default=["本國籍"]
    )
    # 9. 設籍地
    filters["設籍地"] = st.sidebar.multiselect(
        "設籍地",
        options=FILTER_OPTIONS["設籍地"]
    )
    # 10. 就讀地
    filters["就讀地"] = st.sidebar.multiselect(
        "就讀地",
        options=FILTER_OPTIONS["就讀地"]
    )
    # 11. 特殊身份
    filters["特殊身份"] = st.sidebar.multiselect(
        "特殊身份",
        options=FILTER_OPTIONS["特殊身份"]
    )
    # 12. 家庭境遇
    filters["家庭境遇"] = st.sidebar.multiselect(
        "家庭境遇",
        options=FILTER_OPTIONS["家庭境遇"]
    )
    # 13. 經濟相關證明
    filters["經濟相關證明"] = st.sidebar.multiselect(
        "經濟相關證明",
        options=FILTER_OPTIONS["經濟相關證明"]
    )
    # 14. 核心學業要求（百分制）
    filters["核心學業要求"] = st.sidebar.slider("核心學業要求 (分)", min_value=0, max_value=100, value=(0, 100), step=1)
    # 15. 操行(分數)
    filters["操行(分數)"] = st.sidebar.slider("操行 (分)", min_value=0, max_value=100, value=(0, 100), step=1)
    # 16. 操行(獎懲紀錄)
    filters["操行/品德"] = st.sidebar.multiselect(
        "操行/品德（獎懲紀錄）",
        options=FILTER_OPTIONS["操行/品德"]
    )
    
    # ==================== Filter Scholarships ====================
    def get_min_amount_and_quota(scholarship):
        min_amount = None
        min_quota = None
        # Collect all amount/quota from common_tags
        tags = scholarship.get("tags", {})
        for req in tags.get("common_tags", []):
            if req.get("tag_category") == "獎助金額":
                numerical = req.get("numerical")
                if numerical and numerical.get("num_value") is not None:
                    val = numerical.get("num_value")
                    if min_amount is None or val < min_amount:
                        min_amount = val
            if req.get("tag_category") == "獎助名額":
                numerical = req.get("numerical")
                if numerical and numerical.get("num_value") is not None:
                    val = numerical.get("num_value")
                    if min_quota is None or val < min_quota:
                        min_quota = val
        # Collect all amount/quota from groups
        for group in tags.get("groups", []):
            for req in group.get("requirements", []):
                if req.get("tag_category") == "獎助金額":
                    numerical = req.get("numerical")
                    if numerical and numerical.get("num_value") is not None:
                        val = numerical.get("num_value")
                        if min_amount is None or val < min_amount:
                            min_amount = val
                if req.get("tag_category") == "獎助名額":
                    numerical = req.get("numerical")
                    if numerical and numerical.get("num_value") is not None:
                        val = numerical.get("num_value")
                        if min_quota is None or val < min_quota:
                            min_quota = val
        return min_amount, min_quota

    def scholarship_amount_quota_filter(scholarship, amount_range, quota_range):
        min_amount, min_quota = get_min_amount_and_quota(scholarship)
        # If no value, always pass
        if min_amount is None:
            min_amount = 0
        if min_quota is None:
            min_quota = 1
        return (amount_range[0] <= min_amount <= amount_range[1]) and (quota_range[0] <= min_quota <= quota_range[1])

    filtered_scholarships = [
        s for s in scholarships
        if scholarship_amount_quota_filter(s, filters["獎助金額"], filters["獎助名額"]) and check_scholarship_match(s, filters)
    ]
    
    # ==================== 排序選擇器 ====================
    sort_options = {
        "金額（由高到低）": "amount_desc",
        "金額（由低到高）": "amount_asc",
        "名額（由高到低）": "quota_desc",
        "名額（由低到高）": "quota_asc",
        "截止日期（由近到遠）": "date_asc",
        "截止日期（由遠到近）": "date_desc"
    }
    col_title, col_sort = st.columns([6,1])
    with col_title:
        st.markdown(f"### 找到 {len(filtered_scholarships)} 筆符合條件的獎學金")
    with col_sort:
        sort_choice = st.selectbox("排序", list(sort_options.keys()), index=0, label_visibility="collapsed")

    def get_min_amount_and_quota(scholarship):
        min_amount = None
        min_quota = None
        tags = scholarship.get("tags", {})
        for req in tags.get("common_tags", []):
            if req.get("tag_category") == "獎助金額":
                numerical = req.get("numerical")
                if numerical and numerical.get("num_value") is not None:
                    val = numerical.get("num_value")
                    if min_amount is None or val < min_amount:
                        min_amount = val
            if req.get("tag_category") == "獎助名額":
                numerical = req.get("numerical")
                if numerical and numerical.get("num_value") is not None:
                    val = numerical.get("num_value")
                    if min_quota is None or val < min_quota:
                        min_quota = val
        for group in tags.get("groups", []):
            for req in group.get("requirements", []):
                if req.get("tag_category") == "獎助金額":
                    numerical = req.get("numerical")
                    if numerical and numerical.get("num_value") is not None:
                        val = numerical.get("num_value")
                        if min_amount is None or val < min_amount:
                            min_amount = val
                if req.get("tag_category") == "獎助名額":
                    numerical = req.get("numerical")
                    if numerical and numerical.get("num_value") is not None:
                        val = numerical.get("num_value")
                        if min_quota is None or val < min_quota:
                            min_quota = val
        return min_amount, min_quota

    def get_end_date(scholarship):
        date_str = scholarship.get("end_date", "")
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                import datetime
                return datetime.datetime.strptime(date_str, fmt)
            except Exception:
                continue
        return None

    # 排序
    sort_key = sort_options[sort_choice]
    if sort_key == "amount_desc":
        filtered_scholarships = sorted(filtered_scholarships, key=lambda s: get_min_amount_and_quota(s)[0] if get_min_amount_and_quota(s)[0] is not None else -1, reverse=True)
    elif sort_key == "amount_asc":
        filtered_scholarships = sorted(filtered_scholarships, key=lambda s: get_min_amount_and_quota(s)[0] if get_min_amount_and_quota(s)[0] is not None else float('inf'))
    elif sort_key == "quota_desc":
        filtered_scholarships = sorted(filtered_scholarships, key=lambda s: get_min_amount_and_quota(s)[1] if get_min_amount_and_quota(s)[1] is not None else -1, reverse=True)
    elif sort_key == "quota_asc":
        filtered_scholarships = sorted(filtered_scholarships, key=lambda s: get_min_amount_and_quota(s)[1] if get_min_amount_and_quota(s)[1] is not None else float('inf'))
    elif sort_key == "date_asc":
        filtered_scholarships = sorted(filtered_scholarships, key=lambda s: get_end_date(s) if get_end_date(s) is not None else (9999, 12, 31))
    elif sort_key == "date_desc":
        filtered_scholarships = sorted(filtered_scholarships, key=lambda s: get_end_date(s) if get_end_date(s) is not None else (1900, 1, 1), reverse=True)

    # ===== 分頁功能 =====
    PAGE_SIZE = 10
    total_pages = (len(filtered_scholarships) + PAGE_SIZE - 1) // PAGE_SIZE
    page = st.sidebar.number_input("頁碼", min_value=1, max_value=total_pages, value=1, step=1)
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_scholarships = filtered_scholarships[start_idx:end_idx]

    if not page_scholarships:
        st.info("沒有找到符合條件的獎學金。請調整篩選條件或頁碼。")
        return

    for idx, scholarship in enumerate(page_scholarships, start=start_idx + 1):
        with st.expander(f"{scholarship.get('scholarship_name', '未命名獎學金')}", expanded=(idx == start_idx + 1)):
            # ========== Part A: Metadata Header ==========
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**申請期間：** {scholarship.get('start_date', 'N/A')} ~ {scholarship.get('end_date', 'N/A')}")
            with col2:
                url = scholarship.get('url', '')
                if url:
                    st.markdown(f"**[官方公告]({url})**")
            st.divider()
            # ...existing code...
            
            # ========== Part B: Group Requirements (Hard Criteria) ==========
            groups = scholarship.get("tags", {}).get("groups", [])
            common_tags = scholarship.get("tags", {}).get("common_tags", [])
            
            # Display common tags first if they exist
            if common_tags:
                st.markdown("### 共同適用條件")
                # 將獎助金額/名額也納入顯示
                requirements = [req for req in common_tags if req.get("tag_category") not in ["應繳文件", "領獎學金後的義務", "其他（用於無法歸類的特殊要求）"]]
                # 若 common_tags 沒有獎助金額/名額，則補上 AI 數值
                tag_cats = [r.get("tag_category") for r in requirements]
                if "獎助金額" not in tag_cats:
                    ai_amount, raw_amount = extract_numeric_info_from_tags(scholarship.get("tags", {}), "獎助金額")
                    if ai_amount:
                        requirements.append({"tag_category": "獎助金額", "standardized_value": ai_amount, "tag_value": raw_amount})
                if "獎助名額" not in tag_cats:
                    ai_quota, raw_quota = extract_numeric_info_from_tags(scholarship.get("tags", {}), "獎助名額")
                    if ai_quota:
                        requirements.append({"tag_category": "獎助名額", "standardized_value": ai_quota, "tag_value": raw_quota})
                
                if requirements:
                    cols = st.columns(3)
                    for i, req in enumerate(requirements):
                        col = cols[i % 3]
                        val = req.get("standardized_value")
                        numerical = req.get("numerical")
                        tag_category = req.get('tag_category','')
                        tag_value = req.get('tag_value','')
                        # Decide what to display and where to put tooltip
                        if val and val != "—":
                            display = f"<span class='custom-tooltip'><span class='custom-tooltip-value'>{val}</span><span class='custom-tooltip-text'>{tag_value}</span></span>"
                        elif numerical and numerical.get("num_value") is not None:
                            num_val = numerical.get("num_value")
                            unit = numerical.get("unit","")
                            display = f"<span class='custom-tooltip'><span class='custom-tooltip-value'>{num_val}{unit}</span><span class='custom-tooltip-text'>{tag_value}</span></span>"
                        else:
                            display = req.get("tag_value", "")
                        cat_label = tag_category + ("（可選/多選一）" if req.get('condition_type') == '包含' else "")
                        col.markdown(f"<b>{cat_label}</b><br>{display}", unsafe_allow_html=True)
                        # col.markdown(f"<b>{tag_category}</b><br>{display}", unsafe_allow_html=True)
                else:
                    st.info("無硬性條件")
                st.markdown("")
            
            # Display each group
            if groups:
                for group in groups:
                    group_name = group.get("group_name", "未命名組別")
                    st.markdown(f"### {group_name}")
                    # 只顯示硬條件，並補上 AI 金額/名額
                    requirements = [req for req in group.get("requirements", []) if req.get("tag_category") not in ["應繳文件", "領獎學金後的義務", "其他（用於無法歸類的特殊要求）"]]
                    tag_cats = [r.get("tag_category") for r in requirements]
                    if "獎助金額" not in tag_cats:
                        ai_amount, raw_amount = extract_numeric_info_from_tags({"groups": [group]}, "獎助金額")
                        if ai_amount:
                            requirements.append({"tag_category": "獎助金額", "standardized_value": ai_amount, "tag_value": raw_amount})
                    if "獎助名額" not in tag_cats:
                        ai_quota, raw_quota = extract_numeric_info_from_tags({"groups": [group]}, "獎助名額")
                        if ai_quota:
                            requirements.append({"tag_category": "獎助名額", "standardized_value": ai_quota, "tag_value": raw_quota})
                    if requirements:
                        cols = st.columns(3)
                        for i, req in enumerate(requirements):
                            col = cols[i % 3]
                            val = req.get("standardized_value")
                            numerical = req.get("numerical")
                            tag_category = req.get('tag_category','')
                            tag_value = req.get('tag_value','')
                            if val and val != "—":
                                display = f"<span class='custom-tooltip'><span class='custom-tooltip-value'>{val}</span><span class='custom-tooltip-text'>{tag_value}</span></span>"
                            elif numerical and numerical.get("num_value") is not None:
                                num_val = numerical.get("num_value")
                                unit = numerical.get("unit","")
                                display = f"<span class='custom-tooltip'><span class='custom-tooltip-value'>{num_val}{unit}</span><span class='custom-tooltip-text'>{tag_value}</span></span>"
                            else:
                                display = req.get("tag_value", "")
                            cat_label = tag_category + ("（可選/多選一）" if req.get('condition_type') == '包含' else "")
                            col.markdown(f"<b>{cat_label}</b><br>{display}", unsafe_allow_html=True)
                            # col.markdown(f"<b>{tag_category}</b><br>{display}", unsafe_allow_html=True)
                    else:
                        st.info("此組別無特定資格要求（或僅有應繳文件/義務）")
                    
                    # 移除 group 下的應繳文件與義務顯示，改為統一在最下方顯示
                    st.markdown("---")
            else:
                # No groups, display common_tags as single group
                st.markdown("### 申請條件")
                pseudo_group = {"requirements": common_tags}
                df = get_requirements_df(pseudo_group)
                if df is not None:
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Documents & Obligations
                st.markdown("#### 應繳文件與義務")
                c1, c2 = st.columns([2, 3])
                
                with c1:
                    st.markdown("**應繳文件清單 (AI 摘要)**")
                    docs = extract_documents_from_group(pseudo_group)
                    if docs:
                        for doc in docs:
                            st.checkbox(doc, key=f"{scholarship['id']}_single_{doc}", disabled=True, value=False)
                    else:
                        st.caption("_無明確文件清單_")
                    
                    obligations = extract_obligations_from_group(pseudo_group)
                    if obligations:
                        st.markdown("**領獎後義務**")
                        for obl in obligations:
                            st.warning(obl)
                
                with c2:
                    with st.expander("點此對照原始文件說明（含詳細格式）", expanded=False):
                        raw_docs = scholarship.get("required_documents", "無資料")
                        st.info(raw_docs)
                        
                        st.markdown("**原始資格說明：**")
                        st.text(scholarship.get("eligibility", "無資料"))
            
            # ========== Part C: 應繳文件與義務（統一區塊） ========== 
            st.markdown("#### 領獎後義務（所有組別）")
            # 1. 先呈現 common_tags 的義務
            pseudo_group = {"requirements": common_tags}
            obligations = extract_obligations_from_group(pseudo_group)
            if obligations:
                st.markdown("**通用條件**")
                for obl in obligations:
                    st.warning(obl)
            # 2. 再呈現各組的義務
            for group in groups:
                group_name = group.get("group_name", "未命名組別")
                obligations = extract_obligations_from_group(group)
                if obligations:
                    st.markdown(f"**組別：{group_name}**")
                    for obl in obligations:
                        st.warning(obl)
            st.markdown("")

            st.markdown("#### 應繳文件清單（所有組別）")
            # 1. 先呈現 common_tags 的文件
            docs = extract_documents_from_group(pseudo_group)
            if docs:
                st.markdown("**通用條件**")
                for doc in docs:
                    st.markdown(f"- {doc}")
            # 2. 再呈現各組的文件
            for group in groups:
                group_name = group.get("group_name", "未命名組別")
                docs = extract_documents_from_group(group)
                if docs:
                    st.markdown(f"**組別：{group_name}**")
                    for doc in docs:
                        st.markdown(f"- {doc}")
            st.markdown("")

            # ========== Part D: Error Reporting ========== 
            st.markdown("")
            s_id = scholarship.get('id')
            s_name = scholarship.get('scholarship_name', '')
            mailto_link = (
                f"mailto:?subject=[錯誤回報] ID: {s_id} - {s_name}"
                f"&body=請描述您發現的錯誤：%0D%0A%0D%0A"
                f"獎學金 ID: {s_id}%0D%0A"
                f"獎學金名稱: {s_name}%0D%0A"
                f"問題描述: "
            )
            st.link_button("回報錯誤", mailto_link)

if __name__ == "__main__":
    main()

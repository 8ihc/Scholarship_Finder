from collections import defaultdict
import html
import streamlit as st
import pandas as pd
from data_loader import load_scholarships
from filters import check_scholarship_match
from ui_components import get_requirements_df, extract_documents_from_group, extract_obligations_from_group
from constants import FILTER_OPTIONS
from utils import extract_numeric_info_from_tags

st.set_page_config(
    page_title="NTU Scholarship Finder",
    layout="wide"
)

# ==================== Custom CSS Styling ====================
st.markdown("""
<style>
/* ==================== 全域背景與字體 ==================== */
.stApp, .main, header[data-testid="stHeader"], [data-testid="stToolbar"] {
    background-color: #F2F2EC !important;
}
body, p, span, div, label, h1, h2, h3, h4, h5, h6, .stMarkdown, .stMarkdown * {
    color: #594C3B !important;
}
h1 {
    font-size: 4rem;
    color: #594C3B !important;
    border-bottom: 3px solid #D9B91A;
    padding-bottom: 10px;
}
h3, .element-container h3, .element-container h4 {
    color: #594C3B !important;
}

/* ==================== Sidebar ==================== */
[data-testid="stSidebar"] {
    background-color: #F1F2EF;
    border-right: none;
    box-shadow: 2px 0 8px rgba(89, 76, 59, 0.1);
}
[data-testid="stSidebar"] * {
    color: #594C3B !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-weight: bold;
}
[data-testid="stSidebar"] label {
    font-weight: 500;
}
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
[data-testid="stSidebar"] input[type="text"] {
    color: #594C3B !important;
    -webkit-text-fill-color: #594C3B !important;
}
[data-testid="stSidebar"] input::placeholder {
    color: #8B7E6F !important;
    opacity: 0.7;
}
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="input"] span {
    color: #594C3B !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background-color: #D9B91A !important;
    color: #594C3B !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span {
    color: #594C3B !important;
}
[data-testid="stSidebar"] [data-baseweb="select"]:focus,
[data-testid="stSidebar"] [data-baseweb="input"]:focus,
[data-testid="stSidebar"] input:focus {
    border: none !important;
    outline: none !important;
}

/* ==================== Popover ==================== */
[data-baseweb="popover"],
[data-baseweb="popover"] ul,
[data-baseweb="popover"] li {
    background-color: white !important;
    color: #594C3B !important;
}
[data-baseweb="popover"] li:hover {
    background-color: #E3E2DE !important;
}

/* ==================== Expander ==================== */
[data-testid="stExpander"] {
    background-color: white;
    border: none;
    border-radius: 8px;
    margin-bottom: 1rem;
}
[data-testid="stExpander"] summary {
    background-color: rgba(217,185,26,0.85);
    color: #594C3B !important;
    font-weight: bold;
    padding: 0.5rem;
    border-radius: 4px;
}
[data-testid="stExpander"] p,
[data-testid="stExpander"] span,
[data-testid="stExpander"] div {
    color: #594C3B !important;
}
[data-testid="stExpander"] summary:hover {
    background-color: #D9A918;
}

/* ==================== DataFrame ==================== */
[data-testid="stDataFrame"] {
    border: none;
}
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] table,
[data-testid="stDataFrame"] thead th,
[data-testid="stDataFrame"] tbody tr,
[data-testid="stDataFrame"] tbody td,
[data-testid="stDataFrame"] [role="gridcell"],
[data-testid="stDataFrame"] [role="columnheader"] {
    background-color: #F1F2EF !important;
    color: #594C3B !important;
}
[data-testid="stDataFrame"] thead th {
    font-weight: bold;
}
[data-testid="stDataFrame"] tbody tr:hover {
    background-color: #E3E2DE !important;
}

/* ==================== Info/Warning ==================== */
.stInfo {
    background-color: #F2F2EC;
    border-left: none;
}
.stWarning {
    background-color: #FFF9E6;
    border-left: none;
}

/* ==================== Button/Link ==================== */
.stButton > button {
    background-color: #F2F2EC;
    color: #F2F2EC !important;
    border: none;
    padding: 0.5rem 0.5rem;
    font-weight: 600;
    min-width: 120px; /* 讓排序按鈕本身變寬 */
    padding-left: 1.2rem;
    padding-right: 1.2rem;
}
.stButton { margin-right: 0.2rem; }
div[data-testid="column"] > div > .stButton { margin-left: 0.3rem; margin-right: 0.3rem; }

.stButton > button:hover {
    background-color: white ;
    color: white !important;
}
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

/* ==================== Checkbox/Metric ==================== */
[data-testid="stCheckbox"] label,
[data-testid="stMetricValue"] {
    color: #594C3B !important;
}

/* ==================== Custom Tooltip ==================== */
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
    min-width: 200px;
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

# ==================== Helper Functions ====================

#--- 獎助金額與名額過濾器 ---
def scholarship_amount_quota_filter(scholarship, amount_range, quota_range):
        min_amount, min_quota = get_min_amount_and_quota(scholarship)
        if min_amount is None:
            min_amount = 0
        if min_quota is None:
            min_quota = 1
        return (amount_range[0] <= min_amount <= amount_range[1]) and (quota_range[0] <= min_quota <= quota_range[1])

#--- 提取最小金額與名額函式 ---
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

#--- 提取結束日期函式 ---
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

#--- 排序按鈕相關函式 ---
def toggle_sort(key):
        if st.session_state['sort_by'] == key:
            st.session_state['sort_order'] = 'asc' if st.session_state['sort_order'] == 'desc' else 'desc'
        else:
            st.session_state['sort_by'] = key
            if key == 'end_date':
                st.session_state['sort_order'] = 'asc'
            else:
                st.session_state['sort_order'] = 'desc'

#--- 排序按鈕標籤函式 ---
def get_sort_label(label, key):
    if st.session_state['sort_by'] == key:
        arrow = "▼" if st.session_state['sort_order'] == 'desc' else "▲"
        return f"{label} {arrow}"
    return label

#--- 格式化數字函式 ---
def format_number(val, tag_category=None):
    # GPA 例外，其他都取整數
    if tag_category and ("GPA" in tag_category or "平均" in tag_category):
        return val
    try:
        # 若是數字字串也能處理
        return str(int(round(float(val))))
    except Exception:
        return val

# --- 生成 Tooltip HTML ---
def create_tooltip_html(display_text, raw_texts):
    # 過濾空值並去重
    valid_texts = [t for t in raw_texts if t]
    # 如果沒有詳細內容，直接回傳顯示文字
    if not valid_texts:
        return display_text
    
    # 將所有原始說明文字用換行符號接起來，並做 HTML Escape 安全處理
    # 使用 sorted(list(set(...))) 是為了去除完全重複的說明並排序
    unique_texts = sorted(list(set(valid_texts)))
    tooltip_content = "<br>".join([html.escape(t) for t in unique_texts])
    
    return f"""
    <span class='custom-tooltip'>
        <span class='custom-tooltip-value'>{display_text}</span>
        <span class='custom-tooltip-text'>{tooltip_content}</span>
    </span>
    """

# --- 核心渲染函式 (負責分組與畫圖) ---
def render_requirements_grid(requirements_list):
    if not requirements_list:
        return

    # 1. 分組邏輯：將相同「類別」且相同「條件類型」的歸類在一起
    # Key: (類別名稱, 條件類型)
    # Value: [req1, req2, ...] (條件物件的列表)
    grouped_data = defaultdict(list)
    
    for req in requirements_list:
        cat = req.get("tag_category", "其他")
        cond = req.get("condition_type", "")
        grouped_data[(cat, cond)].append(req)

    # 2. 畫圖邏輯
    cols = st.columns(3)
    # 將 dict 轉為 list 以便 enumerate
    grouped_items = list(grouped_data.items())
    
    for i, ((category, condition_type), req_group) in enumerate(grouped_items):
        col = cols[i % 3]
        
        display_values = set()  # 用 set 來自動去除重複的顯示文字 (例如: "其他", "其他" -> "其他")
        tooltip_texts = []      # 收集所有原始說明文字
        
        for req in req_group:
            # 收集 Tooltip 文字
            raw_text = req.get("tag_value", "")
            if raw_text:
                tooltip_texts.append(raw_text)
            
            # 決定卡片上的顯示文字
            val = req.get("standardized_value")
            numerical = req.get("numerical")
            
            d_text = ""
            if val and val != "—":
                d_text = format_number(val, category)
            elif numerical and numerical.get("num_value") is not None:
                unit = numerical.get("unit", "")
                d_text = f"{format_number(numerical.get('num_value'), category)}{unit}"
            else:
                d_text = raw_text
            
            if d_text:
                display_values.add(d_text)
        
        # 3. 組合最終結果
        # 如果集合中有多個不同的值 (例如: "英文", "日文")，用頓號連接
        final_display_str = "、".join(sorted(list(display_values)))
        if not final_display_str:
            final_display_str = "詳見說明" # 防止空白
            
        # 生成帶有 Tooltip 的 HTML
        final_html = create_tooltip_html(final_display_str, tooltip_texts)
        
        # 處理標題
        cat_label = category + ("（可選/多選一）" if condition_type == '包含' else "")
        col.markdown(f"<b>{cat_label}</b><br>{final_html}", unsafe_allow_html=True)

# ==================== Streamlit App ====================
def main():
    st.markdown("""
        <h1 style='font-size:4rem; color:#594C3B; border-bottom:3px solid #D9B91A; padding-bottom:10px;'>NTU Scholarship Finder</h1>
    """, unsafe_allow_html=True)
    st.markdown("### 基於 AI 標籤的智慧篩選與比對工具")
    scholarships = load_scholarships()
    st.sidebar.header("篩選條件")
    filters = {}
    filters["keyword"] = st.sidebar.text_input("", placeholder="輸入欲查詢之關鍵字")
    st.sidebar.markdown("---")
    filters["獎助金額"] = st.sidebar.slider("獎助金額 (元)", min_value=0, max_value=100000, value=(0, 100000), step=1000)
    filters["獎助名額"] = st.sidebar.slider("獎助名額 (人)", min_value=0, max_value=100, value=(0, 100), step=1)
    filters["補助/獎學金排斥"] = st.sidebar.multiselect(
        "補助/獎學金排斥",
        options=FILTER_OPTIONS["補助/獎學金排斥"]
    )
    st.sidebar.markdown("---")
    filters["學制"] = st.sidebar.multiselect(
        "學制",
        options=FILTER_OPTIONS["學制"],
        default=["大學"]
    )
    filters["年級"] = st.sidebar.multiselect(
        "年級",
        options=FILTER_OPTIONS["年級"]
    )
    filters["學籍狀態"] = st.sidebar.multiselect(
        "學籍狀態",
        options=FILTER_OPTIONS["學籍狀態"]
    )
    filters["學院"] = st.sidebar.multiselect(
        "學院",
        options=FILTER_OPTIONS["學院"]
    )
    filters["國籍身分"] = st.sidebar.multiselect(
        "國籍身分",
        options=FILTER_OPTIONS["國籍身分"],
        default=["本國籍"]
    )
    filters["設籍地"] = st.sidebar.multiselect(
        "設籍地",
        options=FILTER_OPTIONS["設籍地"]
    )
    filters["就讀地"] = st.sidebar.multiselect(
        "就讀地",
        options=FILTER_OPTIONS["就讀地"]
    )
    filters["特殊身份"] = st.sidebar.multiselect(
        "特殊身份",
        options=FILTER_OPTIONS["特殊身份"]
    )
    filters["家庭境遇"] = st.sidebar.multiselect(
        "家庭境遇",
        options=FILTER_OPTIONS["家庭境遇"]
    )
    filters["經濟相關證明"] = st.sidebar.multiselect(
        "經濟相關證明",
        options=FILTER_OPTIONS["經濟相關證明"]
    )
    filters["核心學業要求"] = st.sidebar.slider("核心學業要求 (分)", min_value=0, max_value=100, value=(0, 100), step=1)
    filters["操行(分數)"] = st.sidebar.slider("操行 (分)", min_value=0, max_value=100, value=(0, 100), step=1)
    filters["操行/品德"] = st.sidebar.multiselect(
        "操行/品德（獎懲紀錄）",
        options=FILTER_OPTIONS["操行/品德"]
    )

    
    filtered_scholarships = [
        s for s in scholarships
        if scholarship_amount_quota_filter(s, filters["獎助金額"], filters["獎助名額"]) and check_scholarship_match(s, filters)
    ]

    # --- Custom Sort Buttons ---
    # ======= 結果數與排序按鈕同列 =======
    sort_cols = st.columns([5,1,1,1,0.2])
    with sort_cols[0]:
        st.markdown(
            f"""
            <div style='display: flex; align-items: flex-end; height: 48px;'>
                <span style='font-size:1.2rem; font-weight:500; color:#594C3B; margin-bottom:0; padding-bottom:0; line-height:2.5;'>
                    找到 <span style='font-weight:800'>{len(filtered_scholarships)}</span> 筆符合條件的獎學金
                </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    if 'sort_by' not in st.session_state:
        st.session_state['sort_by'] = 'amount'
        st.session_state['sort_order'] = 'desc'

    with sort_cols[1]:
        if st.button(get_sort_label("金額", 'amount'), key='sort_amount'):
            toggle_sort('amount')
            st.rerun()
    with sort_cols[2]:
        if st.button(get_sort_label("名額", 'quota'), key='sort_quota'):
            toggle_sort('quota')
            st.rerun()
    with sort_cols[3]:
        if st.button(get_sort_label("截止日期", 'end_date'), key='sort_enddate'):
            toggle_sort('end_date')
            st.rerun()

    # 排序邏輯
    sort_by = st.session_state['sort_by']
    sort_order = st.session_state['sort_order']
    if sort_by == 'amount':
        filtered_scholarships = sorted(
            filtered_scholarships,
            key=lambda s: get_min_amount_and_quota(s)[0] if get_min_amount_and_quota(s)[0] is not None else -1,
            reverse=(sort_order == 'desc')
        )
    elif sort_by == 'quota':
        filtered_scholarships = sorted(
            filtered_scholarships,
            key=lambda s: get_min_amount_and_quota(s)[1] if get_min_amount_and_quota(s)[1] is not None else -1,
            reverse=(sort_order == 'desc')
        )
    elif sort_by == 'end_date':
        filtered_scholarships = sorted(
            filtered_scholarships,
            key=lambda s: get_end_date(s) if get_end_date(s) is not None else (9999, 12, 31),
            reverse=(sort_order == 'desc')
        )

    # ==================== 分頁邏輯 (Logic) ====================
    PAGE_SIZE = 10
    # 1. 初始化頁碼 Session State
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = 1

    # 2. 計算總頁數
    total_pages = max(1, (len(filtered_scholarships) + PAGE_SIZE - 1) // PAGE_SIZE)

    # 3. 防呆：如果篩選條件改變導致總頁數變少，重置回第1頁
    if st.session_state['current_page'] > total_pages:
        st.session_state['current_page'] = 1

    # 4. 計算切片範圍
    page = st.session_state['current_page']
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE

    # 5. 取得當前頁面的資料
    page_scholarships = filtered_scholarships[start_idx:end_idx]

    if not page_scholarships:
        st.info("沒有找到符合條件的獎學金。請調整篩選條件。")
        # 不 return，讓下方分頁控制列能顯示

    # ==================== 顯示獎學金列表 (List Rendering) ====================

    for idx, scholarship in enumerate(page_scholarships, start=start_idx + 1):
        # ...existing code for scholarship card rendering...
        with st.expander(f"{scholarship.get('scholarship_name', '未命名獎學金')}", expanded=(idx == start_idx + 1)):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**申請期間：** {scholarship.get('start_date', 'N/A')} ~ {scholarship.get('end_date', 'N/A')}")
                # ---------------------------------------------------------
                # 修正後的金額與名額提取邏輯 (同時掃描 Groups 與 Common Tags)
                # ---------------------------------------------------------
                groups = scholarship.get("tags", {}).get("groups", [])
                common_tags = scholarship.get("tags", {}).get("common_tags", [])
                
                amounts = [] # 格式將變為: [(5000, "清寒組每名五千"), (10000, "優秀組每名一萬")]                quotas = []
                quotas = []  # 格式將變為: [(10, "每組十名"), (5, "特殊名額五名")]

                # 1. 建立一個包含所有 requirements 的大列表
                all_requirements = []
                # 加入通用條件
                all_requirements.extend(common_tags)
                # 加入所有組別的條件
                for group in groups:
                    all_requirements.extend(group.get("requirements", []))

                # 2. 遍歷所有條件，提取數值
                for req in all_requirements:
                    cat = req.get("tag_category")
                    raw_text = req.get("tag_value", "") # 取得原始文字
                    
                    # 必須使用安全取值 (or {}) 來防止 NoneType Error
                    numerical_data = req.get("numerical") or {}
                    num_val = numerical_data.get("num_value")
                    
                    # 如果 numerical 沒值，嘗試從 standardized_value 補救 (雖然您的新結構都有 numerical，但防呆總是好的)
                    if num_val is None:
                        std_val = req.get("standardized_value")
                        if std_val and str(std_val).replace(",", "").replace(".", "").isdigit():
                            try:
                                num_val = float(str(std_val).replace(",", ""))
                            except:
                                pass

                    # 提取成功，分類存入
                    if num_val is not None:
                        # 判斷金額
                        if cat == "獎助金額":
                            amounts.append((float(num_val), raw_text))
                        # 判斷名額
                        elif cat == "獎助名額":
                            quotas.append((int(float(num_val)), raw_text))

                # === 輔助函式：用來生成帶有 Tooltip 的 HTML ===
                def create_tooltip_html(display_text, raw_texts):
                    # 過濾掉空字串並去重，然後用換行符號連接
                    valid_texts = [t for t in raw_texts if t]
                    unique_texts = sorted(list(set(valid_texts))) # 去重並排序讓顯示整齊
                    
                    if not unique_texts:
                        return display_text # 如果沒有詳細說明，就直接回傳文字
                        
                    # 組合 Tooltip 內容 (用 <br> 換行，並做 escape 防止 HTML 錯誤)
                    tooltip_content = "<br>".join([html.escape(t) for t in unique_texts])
                    
                    return f"""
                    <span class='custom-tooltip'>
                        <span class='custom-tooltip-value'>{display_text}</span>
                        <span class='custom-tooltip-text'>{tooltip_content}</span>
                    </span>
                    """

                # 3. 顯示金額 (取最小值 ~ 最大值)
                if amounts:
                    # 解開 Tuple: nums 是數字列表, texts 是文字列表
                    nums = [a[0] for a in amounts]
                    texts = [a[1] for a in amounts]
                    
                    min_amt = int(min(nums))
                    max_amt = int(max(nums))
                    
                    if min_amt == max_amt:
                        display_str = f"{min_amt:,} 元"
                    else:
                        display_str = f"{min_amt:,} ~ {max_amt:,} 元"
                    
                    # 生成 Tooltip
                    html_out = create_tooltip_html(display_str, texts)
                    st.markdown(f"**獎助金額：** {html_out}", unsafe_allow_html=True)
                else:
                    st.markdown("**獎助金額：** 詳見官方公告", unsafe_allow_html=True)
                
                # 4. 顯示名額
                # 【新增過濾邏輯】剔除 0 的數值，避免 AI 分析錯誤顯示 "0 名"
                valid_items = [q for q in quotas if q[0] > 0]
                if valid_items:
                    nums = [q[0] for q in valid_items]
                    texts = [q[1] for q in valid_items]
                    
                    min_q = int(min(nums))
                    max_q = int(max(nums))
                    
                    if min_q == max_q:
                        display_str = f"{min_q} 名"
                    else:
                        display_str = f"{min_q} ~ {max_q} 名"
                        
                    html_out = create_tooltip_html(display_str, texts)
                    st.markdown(f"**獎助名額：** {html_out}", unsafe_allow_html=True)
                else:
                    st.markdown("**獎助名額：** 未定 / 詳見公告", unsafe_allow_html=True)
            with col2:
                url = scholarship.get('url', '')
                if url:
                    st.markdown(f"**[官方公告]({url})**")
                app_loc = scholarship.get('application_location', None)
                if app_loc:
                    st.markdown(f"**申請地點：** {app_loc}")
                attachments = scholarship.get('attachments', None)
                if attachments:
                    # 解析多個檔案，並列顯示
                    att_links = []
                    import re
                    for att in attachments.split('|'):
                        att = att.strip()
                        m = re.match(r"(.+?)\s*\[(https?://[^\]]+)\]", att)
                        if m:
                            name, url = m.group(1), m.group(2)
                            att_links.append(f"<a href='{url}' target='_blank'>{name}</a>")
                        else:
                            att_links.append(att)
                    att_html = " | ".join(att_links)
                    st.markdown(f"**附加檔案：** {att_html}", unsafe_allow_html=True)
            
            # st.divider() # 分隔線
            st.markdown("<hr style='border:1px solid #D9B91A; margin:20px 0;'>", unsafe_allow_html=True)

            # ==================== 顯示資格條件 (Requirements Rendering) ====================
            groups = scholarship.get("tags", {}).get("groups", [])
            common_tags = scholarship.get("tags", {}).get("common_tags", [])

            # ==================== 1. 處理共同適用條件 ====================
            if common_tags:
                st.markdown("""
                    <h3 style='margin-bottom:25px; color:#594C3B;'>共同適用</h3>
                """, unsafe_allow_html=True)
                # 過濾不需要顯示的 tags
                requirements = [req for req in common_tags if req.get("tag_category") not in ["應繳文件", "領獎學金後的義務", "其他（用於無法歸類的特殊要求）"]]
                
                # 檢查並補上 AI 提取的金額與名額 (維持你原本的邏輯)
                tag_cats = [r.get("tag_category") for r in requirements]
                
                if "獎助金額" not in tag_cats:
                    ai_amount, raw_amount = extract_numeric_info_from_tags(scholarship.get("tags", {}), "獎助金額")
                    if ai_amount:
                        requirements.append({"tag_category": "獎助金額", "standardized_value": ai_amount, "tag_value": raw_amount})
                        
                if "獎助名額" not in tag_cats:
                    ai_quota, raw_quota = extract_numeric_info_from_tags(scholarship.get("tags", {}), "獎助名額")
                    if ai_quota:
                        requirements.append({"tag_category": "獎助名額", "standardized_value": ai_quota, "tag_value": raw_quota})
                
                # 【修改點】直接呼叫函式渲染，取代原本冗長的 for loop
                if requirements:
                    render_requirements_grid(requirements)
                else:
                    st.info("無硬性條件")
                
                st.markdown("")
            
            st.markdown("<hr style='border:1px solid #D9B91A; margin:20px 0;'>", unsafe_allow_html=True)

            # ==================== 2. 處理各組別 ====================
            if groups:
                st.markdown("""
                    <h3 style='margin-bottom:25px; color:#594C3B;'>子組別適用</h3>
                """, unsafe_allow_html=True)

                for group in groups:
                    group_name = group.get("group_name", "未命名組別")
                    st.markdown(f"""
                        <h4 style='margin-bottom:18px; color:#594C3B; font-size:1.2rem; font-weight:600; background:#FFF3D1; border-radius:8px; padding:6px 18px 6px 12px; display:inline-block;'>{group_name}</h4>
                    """, unsafe_allow_html=True)
                    
                    requirements = [req for req in group.get("requirements", []) if req.get("tag_category") not in ["應繳文件", "領獎學金後的義務", "其他（用於無法歸類的特殊要求）"]]
                    
                    # 同樣檢查並補上 AI 提取的金額與名額
                    tag_cats = [r.get("tag_category") for r in requirements]
                    
                    if "獎助金額" not in tag_cats:
                        ai_amount, raw_amount = extract_numeric_info_from_tags({"groups": [group]}, "獎助金額")
                        if ai_amount:
                            requirements.append({"tag_category": "獎助金額", "standardized_value": ai_amount, "tag_value": raw_amount})
                    
                    if "獎助名額" not in tag_cats:
                        ai_quota, raw_quota = extract_numeric_info_from_tags({"groups": [group]}, "獎助名額")
                        if ai_quota:
                            requirements.append({"tag_category": "獎助名額", "standardized_value": ai_quota, "tag_value": raw_quota})
                    
                    # 【修改點】直接呼叫函式渲染
                    if requirements:
                        render_requirements_grid(requirements)
                    else:
                        st.info("此組別無特定資格要求（或僅有應繳文件/義務）")
                        
                    st.markdown("---")
            
            # ==================== 3. 表格與文件清單 (這部分保持不變) ====================
            else:
                st.markdown("### 申請條件")
                pseudo_group = {"requirements": common_tags}
                df = get_requirements_df(pseudo_group)
                if df is not None:
                    st.dataframe(df, use_container_width=True, hide_index=True)

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

            st.markdown("#### 領獎後義務（所有組別）")
           
            pseudo_group = {"requirements": common_tags}
            obligations = extract_obligations_from_group(pseudo_group)
            if obligations:
                st.markdown("**通用條件**")
                for obl in obligations:
                    st.warning(obl)
            for group in groups:
                group_name = group.get("group_name", "未命名組別")
                obligations = extract_obligations_from_group(group)
                if obligations:
                    st.markdown(f"**組別：{group_name}**")
                    for obl in obligations:
                        st.warning(obl)
            st.markdown("")
            st.markdown("#### 應繳文件清單（所有組別）")
            docs = extract_documents_from_group(pseudo_group)
            if docs:
                st.markdown("**通用條件**")
                for doc in docs:
                    st.markdown(f"- {doc}")
            for group in groups:
                group_name = group.get("group_name", "未命名組別")
                docs = extract_documents_from_group(group)
                if docs:
                    st.markdown(f"**組別：{group_name}**")
                    for doc in docs:
                        st.markdown(f"- {doc}")
            st.markdown("")
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

    st.markdown("---")

    # ==================== 底部頁碼控制列 (Bottom Pagination) ====================
    c1, c2, c3, c4, c5 = st.columns([2, 1, 2, 1, 2])
    with c2:
        if st.button("◀ 上一頁", disabled=(st.session_state['current_page'] == 1), key='prev_page'):
            st.session_state['current_page'] -= 1
            st.rerun()
    with c3:
        st.markdown(
            f"<div style='text-align: center; padding-top: 10px; font-weight: bold; color: #594C3B;'>"
            f"第 {st.session_state['current_page']} 頁 / 共 {total_pages} 頁"
            f"</div>", 
            unsafe_allow_html=True
        )
    with c4:
        if st.button("下一頁 ▶", disabled=(st.session_state['current_page'] == total_pages), key='next_page'):
            st.session_state['current_page'] += 1
            st.rerun()

if __name__ == "__main__":
    main()

from collections import defaultdict
import html
import streamlit as st
import pandas as pd
from data_loader import load_scholarships
from filters import check_scholarship_match, scholarship_amount_quota_filter, check_undetermined_amount
from ui_components import extract_documents_from_group, extract_obligations_from_group, toggle_sort, get_sort_label, create_tooltip_html, render_requirements_grid
from constants import FILTER_OPTIONS, EXCHANGE_RATES
from utils import extract_numeric_info_from_tags, get_min_amount_and_quota, get_end_date, format_number

st.set_page_config(
    page_title="NTU Scholarship Finder",
    layout="wide"
)

def load_css(file_name):
    with open(file_name, encoding='utf-8') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css("app/styles.css")

# ==================== Helper Functions ====================

#--- 獎助金額與名額過濾器 ---
# Moved to filters.py

#--- 提取最小金額與名額函式 ---
# Moved to utils.py

#--- 提取結束日期函式 ---
# Moved to utils.py

#--- 格式化數字函式 ---
# Moved to utils.py

# --- 生成 Tooltip HTML ---
# Moved to ui_components.py

# --- 核心渲染函式 (負責分組與畫圖) ---
# Moved to ui_components.py

# ==================== Streamlit App ====================
@st.dialog("歡迎使用 NTU Scholarship Finder 👋")
def show_welcome_dialog():
    st.markdown("""
    ### 💡 聰明篩選，不錯過任何機會
    
    本系統採用 **「身分資格導向」** 的篩選機制，協助您找到所有符合資格的獎學金。
    
    **舉例來說：**
    如果您在側邊欄選擇 **「社會科學院」**，系統將會為您列出：
    1. ✅ 限定 **「社會科學院」** 的獎學金
    2. ✅ **「不限學院」** 的全校通用獎學金
    
    這樣設計是為了確保您 **不會因為篩選了學院，而錯失了全校皆可申請的機會**！
    
    請放心選擇您的資格與條件，系統會自動幫您過濾出所有您能申請的項目。
    """)
    if st.button("我瞭解了，開始使用", type="primary", use_container_width=True):
        st.session_state['has_seen_welcome'] = True
        st.rerun()

def main():
    if 'has_seen_welcome' not in st.session_state:
        show_welcome_dialog()

    st.markdown("""
        <h1 style='font-size:4rem; color:#594C3B; border-bottom:3px solid #D9B91A; padding-bottom:10px;'>NTU Scholarship Finder</h1>
    """, unsafe_allow_html=True)
    st.markdown("### 基於 AI 標籤的獎學金搜尋工具")
    scholarships = load_scholarships()
    st.sidebar.header("篩選條件")
    filters = {}
    filters["keyword"] = st.sidebar.text_input("關鍵字搜尋", placeholder="輸入欲查詢之關鍵字", key="sidebar_keyword")
    filters["only_undetermined_amount"] = st.sidebar.checkbox("只顯示「金額未定」", value=False)
    
    st.sidebar.markdown("### 學業資格")
    filters["學制"] = st.sidebar.multiselect(
        "學制",
        options=FILTER_OPTIONS["學制"],
        key="filter_degree"
    )
    grade_map = {"1": "一", "2": "二", "3": "三", "4": "四", "4以上": "四年級以上"}
    filters["年級"] = st.sidebar.multiselect(
        "年級",
        options=FILTER_OPTIONS["年級"],
        format_func=lambda x: grade_map.get(x, x),
        key="filter_grade"
    )
    filters["學籍狀態"] = st.sidebar.multiselect(
        "學籍狀態",
        options=FILTER_OPTIONS["學籍狀態"],
        key="filter_status"
    )
    filters["學院"] = st.sidebar.multiselect(
        "學院",
        options=FILTER_OPTIONS["學院"],
        key="filter_college"
    )
    

    st.sidebar.markdown("### 國籍與地區")
    filters["國籍身分"] = st.sidebar.multiselect(
        "國籍身分",
        options=FILTER_OPTIONS["國籍身分"],
        key="filter_nationality"
    )
    filters["設籍地"] = st.sidebar.multiselect(
        "設籍地",
        options=FILTER_OPTIONS["設籍地"],
        key="filter_domicile"
    )
    filters["就讀地"] = st.sidebar.multiselect(
        "就讀地",
        options=FILTER_OPTIONS["就讀地"],
        key="filter_study_loc"
    )

    st.sidebar.markdown("### 身分與特殊境遇")
    filters["經濟相關證明"] = st.sidebar.multiselect(
        "經濟相關證明",
        options=FILTER_OPTIONS["經濟相關證明"],
        key="filter_economic"
    )
    filters["家庭境遇"] = st.sidebar.multiselect(
        "家庭境遇",
        options=FILTER_OPTIONS["家庭境遇"],
        key="filter_family"
    )
    filters["特殊身份"] = st.sidebar.multiselect(
        "特殊身份",
        options=FILTER_OPTIONS["特殊身份"],
        key="filter_special"
    )

    st.sidebar.markdown("### 其他限制")
    filters["補助/獎學金排斥"] = st.sidebar.multiselect("補助/獎學金排斥", FILTER_OPTIONS["補助/獎學金排斥"], key="filter_exclusion")

    # ==================== Filter Logic ====================
    
    # check_undetermined_amount moved to filters.py

    filtered_scholarships = [
        s for s in scholarships
        if check_scholarship_match(s, filters) and (not filters.get("only_undetermined_amount") or check_undetermined_amount(s))
    ]

    # --- Custom Sort Buttons ---
    # ======= 結果數與排序按鈕同列 =======
    sort_cols = st.columns([6,1,1,0.2])
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

                # Debug: 顯示 scholarship ID 和 requirements 數量
                # st.write(f"Debug: ID={scholarship.get('id')}, Groups={len(groups)}, Common={len(common_tags)}")

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
                    unit = numerical_data.get("unit", "")

                    # 如果 numerical 沒值，嘗試從 standardized_value 補救
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
                            # 匯率換算
                            if unit:
                                unit_clean = unit.strip().upper()
                                rate = EXCHANGE_RATES.get(unit_clean)
                                if not rate:
                                    for key, r in EXCHANGE_RATES.items():
                                        if key in unit_clean:
                                            rate = r
                                            break
                                if rate:
                                    num_val = num_val * rate
                            
                            if float(num_val) > 0:
                                amounts.append((float(num_val), raw_text))
                        # 判斷名額
                        elif cat == "獎助名額":
                            quotas.append((int(float(num_val)), raw_text))

                # === 輔助函式：用來生成帶有 Tooltip 的 HTML ===
                # create_tooltip_html moved to ui_components.py

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
                    st.markdown("**獎助金額：** 未定/詳見公告", unsafe_allow_html=True)
                
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
                    st.markdown("**獎助名額：** 未定/詳見公告", unsafe_allow_html=True)
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

            # 特殊處理：如果只有一個組別且沒有共同條件，將該組別視為共同條件顯示
            # 這樣可以避免出現「子組別適用」只有一個「通用組別」的奇怪顯示
            if len(groups) == 1 and not common_tags:
                common_tags = groups[0].get("requirements", [])
                groups = [] # 清空 groups，這樣就不會重複顯示在下方

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
            # (Legacy table rendering removed)

            st.markdown("#### 領獎後義務")
           
            pseudo_group = {"requirements": common_tags}
            obligations = extract_obligations_from_group(pseudo_group)
            if obligations:
                st.markdown("**共同適用**")
                for obl in obligations:
                    st.warning(obl)
            for group in groups:
                group_name = group.get("group_name", "未命名組別")
                obligations = extract_obligations_from_group(group)
                if obligations:
                    st.markdown(f"**{group_name}**")
                    for obl in obligations:
                        st.warning(obl)
            st.markdown("")
            st.markdown("#### 應繳文件清單")
            docs = extract_documents_from_group(pseudo_group)
            if docs:
                st.markdown("**共同適用**")
                for doc in docs:
                    st.markdown(f"- {doc}")
            for group in groups:
                group_name = group.get("group_name", "未命名組別")
                docs = extract_documents_from_group(group)
                if docs:
                    st.markdown(f"**{group_name}**")
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

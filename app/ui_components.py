import pandas as pd
import streamlit as st
from typing import List, Dict

def extract_documents_from_group(group: Dict) -> List[str]:
    docs = []
    for req in group.get("requirements", []):
        if req.get("tag_category") == "應繳文件":
            docs.append(req.get("tag_value", ""))
    return docs

def extract_obligations_from_group(group: Dict) -> List[str]:
    obligations = []
    for req in group.get("requirements", []):
        if req.get("tag_category") == "領獎學金後的義務":
            obligations.append(req.get("tag_value", ""))
    return obligations

from collections import defaultdict
import html
from utils import format_number

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
                if category == "年級":
                    grade_map = {"1": "一", "2": "二", "3": "三", "4": "四", "4以上": "四年級以上"}
                    # Handle comma-separated values if any (though usually standardized_value is single)
                    parts = [grade_map.get(p.strip(), p.strip()) for p in val.split(",")]
                    d_text = "、".join(parts)
                else:
                    d_text = format_number(val, category)
            elif numerical and numerical.get("num_value") is not None:
                num_val = numerical.get("num_value")
                if num_val <= 0:
                    d_text = "未定/詳見公告"
                else:
                    unit = numerical.get("unit") or ""
                    academic_metric = numerical.get("academic_metric") or ""
                    # 如果是 GPA，保留小數點
                    if "GPA" in academic_metric or "GPA" in unit:
                        d_text = f"{num_val}{unit}"
                    else:
                        d_text = f"{format_number(num_val, category)}{unit}"
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


# def get_requirements_df(group: Dict, exclude_categories: List[str] = None) -> pd.DataFrame:
#     if exclude_categories is None:
#         exclude_categories = ["應繳文件", "領獎學金後的義務", "其他（用於無法歸類的特殊要求）", "獎助金額", "獎助名額"]
#     requirements = group.get("requirements", [])
#     filtered_reqs = [
#         req for req in requirements 
#         if req.get("tag_category") not in exclude_categories
#     ]
#     if not filtered_reqs:
#         return None
#     data = []
#     for req in filtered_reqs:
#         row = {
#             "類別": req.get("tag_category", ""),
#             "條件類型": req.get("condition_type", ""),
#             "描述": req.get("tag_value", ""),
#             "標準值": req.get("standardized_value", "—")
#         }
#         numerical = req.get("numerical")
#         if numerical:
#             num_val = numerical.get("num_value")
#             unit = numerical.get("unit", "")
#             if num_val is not None:
#                 row["數值"] = f"{num_val}{unit}"
#             scope = numerical.get("academic_scope")
#             metric = numerical.get("academic_metric")
#             if scope:
#                 row["範圍"] = scope
#             if metric:
#                 row["評估標準"] = metric
#         data.append(row)
#     return pd.DataFrame(data)
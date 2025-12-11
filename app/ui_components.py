import pandas as pd
import streamlit as st
from typing import List, Dict

def get_requirements_df(group: Dict, exclude_categories: List[str] = None) -> pd.DataFrame:
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

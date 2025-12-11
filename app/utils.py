def extract_numeric_info_from_tags(tags: dict, category: str):
    """
    從 common_tags 和 groups 內 requirements 挖出指定 category (如 獎助金額/獎助名額) 的 AI 數值與原文。
    回傳 (num_value+unit, 原文tag_value)，若多個以第一個為主。
    """
    for req in tags.get("common_tags", []):
        if req.get("tag_category") == category:
            numerical = req.get("numerical")
            if numerical and numerical.get("num_value") is not None:
                num_val = numerical.get("num_value")
                unit = numerical.get("unit", "")
                tag_value = req.get("tag_value", "")
                return f"{num_val}{unit}", tag_value
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

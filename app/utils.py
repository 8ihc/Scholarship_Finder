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

from constants import EXCHANGE_RATES

#--- 提取最小金額與名額函式 ---
def get_min_amount_and_quota(scholarship):
    min_amount = None
    min_quota = None
    tags = scholarship.get("tags", {})
    
    def process_amount(req):
        nonlocal min_amount
        numerical = req.get("numerical")
        if numerical and numerical.get("num_value") is not None:
            val = numerical.get("num_value")
            unit = numerical.get("unit", "")
            
            # 匯率換算
            if unit:
                # 簡單正規化 unit (去除空白等)
                unit_clean = unit.strip().upper()
                # 嘗試直接對應
                rate = EXCHANGE_RATES.get(unit_clean)
                # 如果沒有直接對應，嘗試部分對應 (例如 "美元/月")
                if not rate:
                    for key, r in EXCHANGE_RATES.items():
                        if key in unit_clean:
                            rate = r
                            break
                if rate:
                    val = val * rate

            if min_amount is None or val < min_amount:
                min_amount = val

    def process_quota(req):
        nonlocal min_quota
        numerical = req.get("numerical")
        if numerical and numerical.get("num_value") is not None:
            val = numerical.get("num_value")
            if min_quota is None or val < min_quota:
                min_quota = val

    for req in tags.get("common_tags", []):
        if req.get("tag_category") == "獎助金額":
            process_amount(req)
        if req.get("tag_category") == "獎助名額":
            process_quota(req)

    for group in tags.get("groups", []):
        for req in group.get("requirements", []):
            if req.get("tag_category") == "獎助金額":
                process_amount(req)
            if req.get("tag_category") == "獎助名額":
                process_quota(req)
                
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

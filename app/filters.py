from typing import List, Dict

def extract_tags_from_group(group: Dict, category: str) -> List[str]:
    values = []
    for req in group.get("requirements", []):
        if req.get("tag_category") == category:
            std_val = req.get("standardized_value")
            if std_val:
                # 將「轉學生」視為「在學生」
                if std_val == "轉學生":
                    std_val = "在學生"
                    
                if "," in std_val:
                    values.extend([v.strip() for v in std_val.split(",")])
                else:
                    values.append(std_val)
    return values

def check_identity_match(group_tags: List[str], user_identities: List[str]) -> bool:
    if not group_tags:
        return True
    group_set = set(group_tags)
    user_set = set(user_identities)
    if "不限" in group_set:
        return True
    return bool(group_set & user_set)

def check_special_status_match(group_tags: List[str], user_statuses: List[str]) -> bool:
    if not group_tags:
        return True
    group_set = set(group_tags)
    user_set = set(user_statuses)
    return bool(group_set & user_set)

def check_economic_proof_match(group_tags: List[str], user_proofs: List[str]) -> bool:
    if not group_tags:
        return True
    group_set = set(group_tags)
    user_set = set(user_proofs)
    return bool(group_set & user_set)

def check_group_match(group: Dict, filters: Dict) -> bool:
    if filters.get("學制"):
        group_degrees = extract_tags_from_group(group, "學制")
        if group_degrees and not any(d in group_degrees for d in filters["學制"]):
            return False
    if filters.get("年級"):
        group_grades = extract_tags_from_group(group, "年級")
        if group_grades and filters["年級"] not in group_grades:
            return False
    if filters.get("學籍狀態"):
        group_status = set(extract_tags_from_group(group, "學籍狀態"))
        user_status = set(filters["學籍狀態"])
        
        # 定義特殊學籍狀態 (需要白名單驗證)
        special_statuses = {"延畢生", "休學擬復學"}
        
        # 找出使用者選擇的特殊學籍
        user_special = user_status & special_statuses
        
        # 1. 特殊學籍檢查 (嚴格模式)
        # 如果使用者選了特殊學籍，獎學金必須明確包含該狀態 (或標註不限)
        if user_special:
            if "不限" not in group_status:
                # 檢查是否有交集 (即獎學金是否有標註該特殊狀態)
                if not (user_special & group_status):
                    return False
        
        # 2. 一般學籍檢查
        # 若獎學金未標註學籍狀態，預設僅限「在學生」(一般生)
        if not group_status:
            group_status = {"在學生"}
            
        # 如果獎學金有指定狀態 (且不是不限)，則必須與使用者選擇的有交集
        if "不限" not in group_status:
            if not (user_status & group_status):
                return False
    if filters.get("學院"):
        group_colleges = extract_tags_from_group(group, "學院")
        if group_colleges and not any(c in group_colleges for c in filters["學院"]):
            return False
    if filters.get("國籍身分"):
        group_identities = extract_tags_from_group(group, "國籍身分")
        if not check_identity_match(group_identities, filters["國籍身分"]):
            return False
    if filters.get("設籍地") and filters["設籍地"] != "不限":
        group_domicile = extract_tags_from_group(group, "設籍地")
        if group_domicile and "不限" not in group_domicile and filters["設籍地"] not in group_domicile:
            return False
    if filters.get("就讀地") and filters["就讀地"] != "不限":
        group_study_loc = extract_tags_from_group(group, "就讀地")
        if group_study_loc and "不限" not in group_study_loc and filters["就讀地"] not in group_study_loc:
            return False
    if filters.get("特殊身份"):
        group_special = extract_tags_from_group(group, "特殊身份")
        if not check_special_status_match(group_special, filters["特殊身份"]):
            return False
    if filters.get("家庭境遇"):
        group_family = extract_tags_from_group(group, "家庭境遇")
        if not check_special_status_match(group_family, filters["家庭境遇"]):
            return False
    if filters.get("經濟相關證明"):
        group_economic = extract_tags_from_group(group, "經濟相關證明")
        if not check_economic_proof_match(group_economic, filters["經濟相關證明"]):
            return False
    return True

def check_scholarship_match(scholarship: Dict, filters: Dict) -> bool:
    if filters.get("keyword"):
        keyword = filters["keyword"].lower()
        searchable_text = f"{scholarship.get('scholarship_name', '')} {scholarship.get('eligibility', '')}".lower()
        if keyword not in searchable_text:
            return False
    groups = scholarship.get("tags", {}).get("groups", [])
    common_tags = scholarship.get("tags", {}).get("common_tags", [])
    if not groups:
        pseudo_group = {"requirements": common_tags}
        return check_group_match(pseudo_group, filters)
    for group in groups:
        combined_group = {
            "requirements": group.get("requirements", []) + common_tags
        }
        if check_group_match(combined_group, filters):
            return True
    return False

from utils import get_min_amount_and_quota

#--- 獎助金額與名額過濾器 ---
def scholarship_amount_quota_filter(scholarship, amount_range, quota_range):
        min_amount, min_quota = get_min_amount_and_quota(scholarship)
        if min_amount is None:
            min_amount = 0
        if min_quota is None:
            min_quota = 1
        return (amount_range[0] <= min_amount <= amount_range[1]) and (quota_range[0] <= min_quota <= quota_range[1])

def check_undetermined_amount(scholarship):
    # Return True if amount is undetermined (None or 0)
    tags = scholarship.get("tags", {})
    # Check common tags
    for req in tags.get("common_tags", []):
        if req.get("tag_category") == "獎助金額":
            numerical = req.get("numerical")
            if numerical and numerical.get("num_value") is not None and numerical.get("num_value") > 0:
                return False
    # Check groups
    for group in tags.get("groups", []):
        for req in group.get("requirements", []):
            if req.get("tag_category") == "獎助金額":
                numerical = req.get("numerical")
                if numerical and numerical.get("num_value") is not None and numerical.get("num_value") > 0:
                    return False
    return True

from typing import List, Dict
from utils import get_min_amount_and_quota


def extract_tags_from_group(group: Dict, category: str) -> List[str]:
    """
    從獎學金的 group 中提取指定類別的標籤值
    
    Args:
        group (Dict): 獎學金的 group 資料，包含 requirements 列表
        category (str): 要提取的標籤類別（例如："學制"、"年級"、"學籍狀態"等）
    
    Returns:
        List[str]: 提取出的標籤值列表
        
    Note:
        - 會自動將「轉學生」轉換為「在學生」
        - 支援逗號分隔的多值標籤（例如："大學部,碩士班"）
    """
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
    """
    檢查國籍身分是否匹配
    
    Args:
        group_tags (List[str]): 獎學金要求的國籍身分標籤列表
        user_identities (List[str]): 使用者選擇的國籍身分列表
    
    Returns:
        bool: 如果匹配則返回 True，否則返回 False
        
    Note:
        - 如果 group_tags 為空，視為不限制，返回 True
        - 如果 group_tags 包含「不限」，返回 True
        - 否則檢查兩個集合是否有交集
    """
    if not group_tags:
        return True
    group_set = set(group_tags)
    user_set = set(user_identities)
    if "不限" in group_set:
        return True
    return bool(group_set & user_set)

def check_special_status_match(group_tags: List[str], user_statuses: List[str]) -> bool:
    """
    檢查特殊身份或家庭境遇是否匹配
    
    Args:
        group_tags (List[str]): 獎學金要求的特殊身份/家庭境遇標籤列表
        user_statuses (List[str]): 使用者選擇的特殊身份/家庭境遇列表
    
    Returns:
        bool: 如果匹配則返回 True，否則返回 False
        
    Note:
        - 如果 group_tags 為空，視為不限制，返回 True
        - 檢查兩個集合是否有交集（使用者至少符合一項要求）
    """
    if not group_tags:
        return True
    group_set = set(group_tags)
    user_set = set(user_statuses)
    return bool(group_set & user_set)

def check_economic_proof_match(group_tags: List[str], user_proofs: List[str]) -> bool:
    """
    檢查經濟相關證明是否匹配
    
    Args:
        group_tags (List[str]): 獎學金要求的經濟證明標籤列表
        user_proofs (List[str]): 使用者選擇的經濟證明列表
    
    Returns:
        bool: 如果匹配則返回 True，否則返回 False
        
    Note:
        - 如果 group_tags 為空，視為不限制，返回 True
        - 檢查兩個集合是否有交集（使用者至少持有一項證明）
    """
    if not group_tags:
        return True
    group_set = set(group_tags)
    user_set = set(user_proofs)
    return bool(group_set & user_set)

def check_group_match(group: Dict, filters: Dict) -> bool:
    """
    檢查獎學金的 group 是否符合使用者的所有篩選條件
    
    這是核心的過濾邏輯函數，會依序檢查以下條件：
    - 學制（大學部、碩士班等）
    - 年級
    - 學籍狀態（在學生、延畢生、休學擬復學等，含特殊邏輯處理）
    - 學院
    - 國籍身分
    - 設籍地
    - 就讀地
    - 特殊身份
    - 家庭境遇
    - 經濟相關證明
    
    Args:
        group (Dict): 獎學金的 group 資料，包含 requirements 列表
        filters (Dict): 使用者在 sidebar 選擇的篩選條件字典
    
    Returns:
        bool: 如果所有條件都符合則返回 True，任一條件不符合則返回 False
        
    Note:
        - 學籍狀態有特殊處理：延畢生和休學擬復學需要獎學金明確標註才會顯示
        - 如果獎學金未標註學籍狀態，預設僅限「在學生」
    """
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
    """
    檢查獎學金是否符合使用者的篩選條件（最上層的過濾函數）
    
    處理流程：
    1. 先檢查關鍵字搜尋（在獎學金名稱和資格條件中搜尋）
    2. 取得獎學金的 groups 和 common_tags
    3. 如果沒有 groups，使用 common_tags 建立 pseudo_group 進行檢查
    4. 如果有 groups，逐一檢查每個 group（結合 common_tags）
    5. 只要有任一 group 符合條件，就返回 True
    
    Args:
        scholarship (Dict): 獎學金完整資料
        filters (Dict): 使用者在 sidebar 選擇的篩選條件字典
    
    Returns:
        bool: 如果獎學金符合篩選條件則返回 True，否則返回 False
        
    Note:
        - 關鍵字搜尋不區分大小寫
        - 獎學金只要有一個 group 符合條件即可顯示（OR 邏輯）
    """
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


#--- 獎助金額與名額過濾器 ---
def scholarship_amount_quota_filter(scholarship, amount_range, quota_range):
    """
    根據獎助金額和名額範圍過濾獎學金
    
    Args:
        scholarship (Dict): 獎學金資料
        amount_range (tuple): 金額範圍 (最小值, 最大值)
        quota_range (tuple): 名額範圍 (最小值, 最大值)
    
    Returns:
        bool: 如果獎學金的金額和名額都在指定範圍內則返回 True
        
    Note:
        - 如果金額為 None，視為 0
        - 如果名額為 None，視為 1
    """
    min_amount, min_quota = get_min_amount_and_quota(scholarship)
    if min_amount is None:
        min_amount = 0
    if min_quota is None:
        min_quota = 1
    return (amount_range[0] <= min_amount <= amount_range[1]) and (quota_range[0] <= min_quota <= quota_range[1])

def check_undetermined_amount(scholarship):
    """
    檢查獎學金的金額是否為未定（None 或 0）
    
    會檢查 common_tags 和所有 groups 中的「獎助金額」標籤，
    只要有任一處標註了明確的金額（> 0），就視為已確定金額。
    
    Args:
        scholarship (Dict): 獎學金資料
    
    Returns:
        bool: 如果金額未定則返回 True，如果有明確金額則返回 False
        
    Note:
        - 用於「顯示未定金額獎學金」的篩選功能
        - 會同時檢查 common_tags 和 groups 中的金額資訊
    """
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

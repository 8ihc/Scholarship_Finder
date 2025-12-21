"""
新版過濾邏輯 (v2)

設計原則：
1. 包容性過濾：使用者選擇的條件代表「我符合這個條件，請幫我找出我可以申請的獎學金」
2. 一般條件（年級、學制等）：未標註 = 不限 = 顯示
3. 特殊身份（延畢生等）：未標註 = 僅限一般生 = 需明確標註才顯示
"""

from typing import List, Dict, Set, Optional
from utils import get_min_amount_and_quota


# ==================== 配置 ====================

# 特殊學籍狀態：需要明確標註才會顯示（白名單邏輯）
SPECIAL_STUDENT_STATUS = {"延畢生", "休學生"}

# 一般條件欄位：未標註視為不限（包容性邏輯）
INCLUSIVE_FIELDS = {"學制", "年級", "學院", "設籍地", "就讀地"}


# ==================== 核心過濾函數 ====================

def is_negative_condition(tag_value: str) -> bool:
    """
    檢查標籤值是否為否定條件（例如：「XXX不得申請」）
    
    Args:
        tag_value (str): 標籤的原始文字值
    
    Returns:
        bool: 如果是否定條件則返回 True
        
    Note:
        - 只有當整個句子主要表達否定意思時才返回 True
        - 如果句子中既有包含又有排除（如「大學...不包含研究生」），返回 False
    """
    # 強否定關鍵字：整句都是否定的
    strong_negative_keywords = [
        "不得申請", "不可申請", "不得", "不可",
        "排除", "除外"
    ]
    
    # 檢查是否以「非」開頭（例如：「非延畢者」）
    if tag_value.startswith("非"):
        return True
    
    # 檢查是否以強否定關鍵字開頭或主要是否定句
    for keyword in strong_negative_keywords:
        if tag_value.startswith(keyword) or (keyword in tag_value and len(tag_value) < 20):
            return True
    
    # 如果包含「不包含」或「不含」，但句子很長（>30字），可能是混合條件
    # 例如：「就讀大學...不包含研究生」→ 這不是純否定條件
    if ("不包含" in tag_value or "不含" in tag_value) and len(tag_value) > 30:
        return False
    
    # 短句中的「不包含」視為否定條件
    if "不包含" in tag_value or "不含" in tag_value:
        return True
    
    return False


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
        - 對於混合條件（既有包含又有排除），只提取包含部分
    """
    values = []
    
    for req in group.get("requirements", []):
        if req.get("tag_category") == category:
            std_val = req.get("standardized_value")
            tag_value = req.get("tag_value", "")
            
            if std_val:
                # 檢查是否為純否定條件
                if is_negative_condition(tag_value):
                    # 這是一個純否定條件，跳過（在 extract_excluded_tags_from_group 中處理）
                    continue
                else:
                    # 正常的包含條件（或混合條件，我們只取包含部分）
                    # 將「轉學生」視為「在學生」
                    if std_val == "轉學生":
                        std_val = "在學生"
                    # 將「新住民」視為「本國籍」（僅限「國籍身分」類別）
                    elif std_val == "新住民" and category == "國籍身分":
                        std_val = "本國籍"
                    # 將「臺灣」視為「不限」（就讀地）
                    elif std_val == "臺灣":
                        std_val = "不限"
                    # 將「清寒證明」視為「村里長提供之清寒證明」
                    elif std_val == "清寒證明":
                        std_val = "村里長提供之清寒證明"
                    # 將錯誤分類的「導師提供之清寒證明」和「村里長提供之清寒證明」歸類到「其他」
                    # （這些應該在「經濟相關證明」類別，但 AI 錯誤地標註在「家庭境遇」）
                    elif category == "家庭境遇" and std_val in ["導師提供之清寒證明", "村里長提供之清寒證明"]:
                        std_val = "其他"
                        
                    if "," in std_val:
                        values.extend([v.strip() for v in std_val.split(",")])
                    else:
                        values.append(std_val)
    
    return values


def extract_excluded_tags_from_group(group: Dict, category: str) -> List[str]:
    """
    從獎學金的 group 中提取指定類別的排除標籤值（否定條件）
    
    Args:
        group (Dict): 獎學金的 group 資料，包含 requirements 列表
        category (str): 要提取的標籤類別
    
    Returns:
        List[str]: 被排除的標籤值列表（例如：「碩博士班不得申請」會返回 ["碩士", "博士"]）
        
    Note:
        - 只提取否定條件中的值
        - 用於檢查使用者選擇的條件是否在排除列表中
        - 如果 standardized_value 是 null，會嘗試從 tag_value 推斷
    """
    excluded_values = []
    
    for req in group.get("requirements", []):
        if req.get("tag_category") == category:
            std_val = req.get("standardized_value")
            tag_value = req.get("tag_value", "")
            
            if is_negative_condition(tag_value):
                # 這是一個排除條件
                if std_val:
                    # 有 standardized_value，直接使用
                    if "," in std_val:
                        excluded_values.extend([v.strip() for v in std_val.split(",")])
                    else:
                        excluded_values.append(std_val)
                else:
                    # standardized_value 是 null，嘗試從 tag_value 推斷
                    # 例如：「非延畢者」→ 排除「延畢生」
                    if category == "學籍狀態":
                        if "延畢" in tag_value:
                            excluded_values.append("延畢生")
                        elif "休學" in tag_value:
                            excluded_values.append("休學生")
                    # 可以為其他 category 添加類似的推斷邏輯
    
    return excluded_values



def check_field_match(
    group_tags: List[str], 
    user_selections: List[str], 
    field_name: str,
    is_special_field: bool = False
) -> bool:
    """
    檢查獎學金的某個欄位是否符合使用者的選擇
    
    Args:
        group_tags (List[str]): 獎學金在該欄位的標籤值列表
        user_selections (List[str]): 使用者在該欄位的選擇列表
        field_name (str): 欄位名稱（用於調試）
        is_special_field (bool): 是否為特殊欄位（使用白名單邏輯）
    
    Returns:
        bool: 如果符合則返回 True，否則返回 False
        
    邏輯：
        包容性邏輯（一般欄位）：
        - 如果 group_tags 為空 → 視為不限 → 返回 True
        - 如果 group_tags 包含「不限」→ 返回 True
        - 如果 group_tags 與 user_selections 有交集 → 返回 True
        - 否則 → 返回 False
        
        白名單邏輯（特殊欄位）：
        - 如果 group_tags 為空 → 視為僅限一般生 → 返回 False
        - 如果 group_tags 包含「不限」→ 返回 True
        - 如果 group_tags 與 user_selections 有交集 → 返回 True
        - 否則 → 返回 False
    """
    # 如果獎學金沒有標註該欄位
    if not group_tags:
        # 特殊欄位：未標註 = 僅限一般生 = 不符合
        if is_special_field:
            return False
        # 一般欄位：未標註 = 不限 = 符合
        else:
            return True
    
    group_set = set(group_tags)
    user_set = set(user_selections)
    
    # 如果獎學金標註「不限」，任何選擇都符合
    if "不限" in group_set:
        return True
    
    # 檢查是否有交集（使用者的選擇是否在獎學金的要求中）
    return bool(group_set & user_set)


def check_student_status_match(group_tags: List[str], user_statuses: List[str]) -> bool:
    """
    檢查學籍狀態是否匹配（特殊處理邏輯）
    
    Args:
        group_tags (List[str]): 獎學金要求的學籍狀態標籤列表
        user_statuses (List[str]): 使用者選擇的學籍狀態列表
    
    Returns:
        bool: 如果匹配則返回 True，否則返回 False
        
    邏輯：
        1. 找出使用者選擇的特殊學籍（延畢生、休學擬復學）
        2. 如果使用者選了特殊學籍：
           - 獎學金必須明確標註該特殊學籍或「不限」
        3. 如果獎學金未標註學籍狀態：
           - 預設僅限「在學生」
        4. 檢查獎學金的學籍狀態與使用者選擇是否有交集
    """
    group_status = set(group_tags) if group_tags else set()
    user_status = set(user_statuses)
    
    # 找出使用者選擇的特殊學籍
    user_special = user_status & SPECIAL_STUDENT_STATUS
    
    # 1. 特殊學籍檢查（嚴格模式）
    # 如果使用者選了特殊學籍，獎學金必須明確包含該狀態（或標註不限）
    if user_special:
        if "不限" not in group_status:
            # 檢查是否有交集（即獎學金是否有標註該特殊狀態）
            if not (user_special & group_status):
                return False
    
    # 2. 一般學籍檢查
    # 若獎學金未標註學籍狀態，預設僅限「在學生」（一般生）
    if not group_status:
        group_status = {"在學生"}
    
    # 如果獎學金有指定狀態（且不是不限），則必須與使用者選擇的有交集
    if "不限" not in group_status:
        if not (user_status & group_status):
            return False
    
    return True


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


def check_multi_select_match(group_tags: List[str], user_selections: List[str]) -> bool:
    """
    檢查多選欄位是否匹配（特殊身份、家庭境遇、經濟證明等）
    
    Args:
        group_tags (List[str]): 獎學金要求的標籤列表
        user_selections (List[str]): 使用者選擇的列表
    
    Returns:
        bool: 如果匹配則返回 True，否則返回 False
        
    Note:
        - 如果 group_tags 為空，視為不限制，返回 True
        - 檢查兩個集合是否有交集（使用者至少符合一項要求）
    """
    if not group_tags:
        return True
    group_set = set(group_tags)
    user_set = set(user_selections)
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
    - 補助/獎學金排斥
    
    Args:
        group (Dict): 獎學金的 group 資料，包含 requirements 列表
        filters (Dict): 使用者在 sidebar 選擇的篩選條件字典
    
    Returns:
        bool: 如果所有條件都符合則返回 True，任一條件不符合則返回 False
        
    Note:
        - 使用新的包容性過濾邏輯
        - 學籍狀態有特殊處理：延畢生和休學擬復學需要獎學金明確標註才會顯示
        - 會檢查排除條件：如果使用者選擇的值在排除列表中，則不顯示該獎學金
    """
    # 學制檢查（精確匹配邏輯）
    if filters.get("學制"):
        group_degrees = extract_tags_from_group(group, "學制")
        excluded_degrees = extract_excluded_tags_from_group(group, "學制")
        
        user_degrees_set = set(filters["學制"])
        excluded_set = set(excluded_degrees)
        
        # 1. 檢查排除條件（改進邏輯）
        # 只有當使用者選擇的所有選項都在排除列表中時，才排除
        # 例如：使用者選「大學」+「其他」，獎學金排除「其他」但有「大學」→ 應該顯示
        non_excluded_degrees = user_degrees_set - excluded_set
        if not non_excluded_degrees:
            # 使用者選擇的所有學制都在排除列表中，不顯示
            return False
        
        # 2. 處理「不限/未明定」選項（OR 邏輯）
        has_undetermined = "不限/未明定" in user_degrees_set
        other_degrees = user_degrees_set - {"不限/未明定"}
        
        # 情況 1: 只選「不限/未明定」
        if has_undetermined and not other_degrees:
            # 只顯示沒有標註學制的獎學金
            if group_degrees:
                return False
        # 情況 2: 只選具體學制（沒選「不限/未明定」）
        elif not has_undetermined and other_degrees:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not group_degrees:
                return False
            if not (other_degrees & set(group_degrees)):
                return False
        # 情況 3: 同時選「不限/未明定」和具體學制（OR 邏輯）
        elif has_undetermined and other_degrees:
            # 顯示：沒有標註的 OR 有標註且符合的
            if group_degrees:
                # 有標註，檢查是否符合使用者選擇的具體學制
                if not (other_degrees & set(group_degrees)):
                    return False
            # 沒有標註的會通過（符合「不限/未明定」）
    
    # 年級檢查（精確匹配邏輯）
    if filters.get("年級"):
        group_grades = extract_tags_from_group(group, "年級")
        excluded_grades = extract_excluded_tags_from_group(group, "年級")
        
        user_grades = filters["年級"]  # 這已經是列表了，不需要再包裝
        user_grades_set = set(user_grades)
        excluded_set = set(excluded_grades)
        
        # 1. 檢查排除條件（改進邏輯）
        # 只有當使用者選擇的所有選項都在排除列表中時，才排除
        non_excluded_grades = user_grades_set - excluded_set
        if not non_excluded_grades:
            # 使用者選擇的所有年級都在排除列表中，不顯示
            return False
        
        # 2. 處理「不限/未明定」選項（OR 邏輯）
        has_undetermined = "不限/未明定" in user_grades_set
        other_grades = user_grades_set - {"不限/未明定"}
        
        # 情況 1: 只選「不限/未明定」
        if has_undetermined and not other_grades:
            # 只顯示沒有標註年級的獎學金
            if group_grades:
                return False
        # 情況 2: 只選具體年級（沒選「不限/未明定」）
        elif not has_undetermined and other_grades:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not group_grades:
                return False
            if not (other_grades & set(group_grades)):
                return False
        # 情況 3: 同時選「不限/未明定」和具體年級（OR 邏輯）
        elif has_undetermined and other_grades:
            # 顯示：沒有標註的 OR 有標註且符合的
            if group_grades:
                # 有標註，檢查是否符合使用者選擇的具體年級
                if not (other_grades & set(group_grades)):
                    return False
            # 沒有標註的會通過（符合「不限/未明定」）
    
    # 學籍狀態檢查（含特殊邏輯和「不限/未明定」）
    if filters.get("學籍狀態"):
        group_status = extract_tags_from_group(group, "學籍狀態")
        excluded_status = extract_excluded_tags_from_group(group, "學籍狀態")
        
        user_status_list = filters["學籍狀態"]
        user_status_set = set(user_status_list)
        excluded_set = set(excluded_status)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_status = user_status_set - excluded_set
        if not non_excluded_status:
            # 使用者選擇的所有學籍狀態都在排除列表中，不顯示
            return False
        
        # 2. 處理「不限/未明定」選項（OR 邏輯）
        has_undetermined = "不限/未明定" in user_status_set
        other_status = user_status_set - {"不限/未明定"}
        
        # 情況 1: 只選「不限/未明定」
        if has_undetermined and not other_status:
            # 只顯示沒有標註學籍狀態的獎學金
            if group_status:
                return False
        # 情況 2: 只選具體學籍狀態（沒選「不限/未明定」）
        elif not has_undetermined and other_status:
            # 3. 特殊身份白名單邏輯（延畢生、休學擬復學）
            user_special = other_status & SPECIAL_STUDENT_STATUS
            user_normal = other_status - SPECIAL_STUDENT_STATUS
            
            # 分別檢查特殊學籍和一般學籍
            special_match = False
            normal_match = False
            
            if user_special:
                # 使用者選了特殊學籍（延畢生或休學擬復學）
                if group_status:
                    # 獎學金有標註學籍狀態，檢查是否包含特殊學籍
                    if user_special & set(group_status):
                        special_match = True
                # 如果獎學金沒有標註學籍狀態，特殊學籍不符合（預設僅限在學生）
            
            if user_normal:
                # 使用者選了一般學籍
                if not group_status:
                    # 獎學金未標註學籍狀態，不顯示
                    pass  # normal_match 保持 False
                else:
                    # 獎學金有標註學籍狀態，檢查是否有交集
                    if user_normal & set(group_status):
                        normal_match = True
            
            # OR 邏輯：只要特殊學籍或一般學籍有一個符合就顯示
            if user_special and user_normal:
                # 同時選了特殊和一般學籍
                if not (special_match or normal_match):
                    return False
            elif user_special:
                # 只選了特殊學籍
                if not special_match:
                    return False
            elif user_normal:
                # 只選了一般學籍
                if not normal_match:
                    return False
        # 情況 3: 同時選「不限/未明定」和具體學籍狀態（OR 邏輯）
        elif has_undetermined and other_status:
            # 顯示：沒有標註的 OR 有標註且符合的
            if group_status:
                # 有標註，需要檢查特殊邏輯
                user_special = other_status & SPECIAL_STUDENT_STATUS
                
                if user_special:
                    # 使用者選了特殊學籍，必須明確包含
                    if not (user_special & set(group_status)):
                        return False
                else:
                    # 一般學籍，檢查交集
                    if not (other_status & set(group_status)):
                        return False
            # 沒有標註的會通過（符合「不限/未明定」）
    
    # 學院檢查（精確匹配邏輯）
    if filters.get("學院"):
        group_colleges = extract_tags_from_group(group, "學院")
        excluded_colleges = extract_excluded_tags_from_group(group, "學院")
        
        user_colleges_set = set(filters["學院"])
        excluded_set = set(excluded_colleges)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_colleges = user_colleges_set - excluded_set
        if not non_excluded_colleges:
            # 使用者選擇的所有學院都在排除列表中，不顯示
            return False
        
        # 2. 處理「不限/未明定」選項（OR 邏輯）
        has_undetermined = "不限/未明定" in user_colleges_set
        other_colleges = user_colleges_set - {"不限/未明定"}
        
        # 將標註「不限」的獎學金視為未標註
        effective_colleges = [c for c in group_colleges if c != "不限"]
        
        # 情況 1: 只選「不限/未明定」
        if has_undetermined and not other_colleges:
            # 只顯示沒有標註學院的獎學金（或只標註「不限」的）
            if effective_colleges:
                return False
        # 情況 2: 只選具體學院（沒選「不限/未明定」）
        elif not has_undetermined and other_colleges:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not effective_colleges:
                return False
            if not (other_colleges & set(effective_colleges)):
                return False
        # 情況 3: 同時選「不限/未明定」和具體學院（OR 邏輯）
        elif has_undetermined and other_colleges:
            # 顯示：沒有標註的 OR 有標註且符合的
            if effective_colleges:
                # 有標註，檢查是否符合使用者選擇的具體學院
                if not (other_colleges & set(effective_colleges)):
                    return False
            # 沒有標註的會通過（符合「不限/未明定」）
    
    # 國籍身分檢查（精確匹配邏輯）
    if filters.get("國籍身分"):
        group_identities = extract_tags_from_group(group, "國籍身分")
        excluded_identities = extract_excluded_tags_from_group(group, "國籍身分")
        
        user_identities_set = set(filters["國籍身分"])
        excluded_set = set(excluded_identities)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_identities = user_identities_set - excluded_set
        if not non_excluded_identities:
            # 使用者選擇的所有國籍身分都在排除列表中，不顯示
            return False
        
        # 2. 處理「不限/未明定」選項（OR 邏輯）
        has_undetermined = "不限/未明定" in user_identities_set
        other_identities = user_identities_set - {"不限/未明定"}
        
        # 將標註「不限」的獎學金視為未標註
        effective_identities = [i for i in group_identities if i != "不限"]
        
        # 情況 1: 只選「不限/未明定」
        if has_undetermined and not other_identities:
            # 只顯示沒有標註國籍身分的獎學金（或只標註「不限」的）
            if effective_identities:
                return False
        # 情況 2: 只選具體國籍身分（沒選「不限/未明定」）
        elif not has_undetermined and other_identities:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not effective_identities:
                return False
            if not (other_identities & set(effective_identities)):
                return False
        # 情況 3: 同時選「不限/未明定」和具體國籍身分（OR 邏輯）
        elif has_undetermined and other_identities:
            # 顯示：沒有標註的 OR 有標註且符合的
            if effective_identities:
                # 有標註，檢查是否符合使用者選擇的具體國籍身分
                if not (other_identities & set(effective_identities)):
                    return False
            # 沒有標註的會通過（符合「不限/未明定」）
    
    # 設籍地檢查（精確匹配邏輯，支援多選）
    if filters.get("設籍地"):
        group_domicile = extract_tags_from_group(group, "設籍地")
        excluded_domicile = extract_excluded_tags_from_group(group, "設籍地")
        
        user_domiciles = filters["設籍地"]  # 這是一個列表
        user_domiciles_set = set(user_domiciles)
        excluded_set = set(excluded_domicile)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_domiciles = user_domiciles_set - excluded_set
        if not non_excluded_domiciles:
            # 使用者選擇的所有設籍地都在排除列表中，不顯示
            return False
        
        # 2. 處理「不限/未明定」選項（OR 邏輯）
        has_undetermined = "不限/未明定" in user_domiciles_set
        other_domiciles = user_domiciles_set - {"不限/未明定"}
        
        # 將標註「不限」的獎學金視為未標註
        effective_domiciles = [d for d in group_domicile if d != "不限"]
        
        # 情況 1: 只選「不限/未明定」
        if has_undetermined and not other_domiciles:
            # 只顯示沒有標註設籍地的獎學金（或只標註「不限」的）
            if effective_domiciles:
                return False
        # 情況 2: 只選具體設籍地（沒選「不限/未明定」）
        elif not has_undetermined and other_domiciles:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not effective_domiciles:
                return False
            if not (other_domiciles & set(effective_domiciles)):
                return False
        # 情況 3: 同時選「不限/未明定」和具體設籍地（OR 邏輯）
        elif has_undetermined and other_domiciles:
            # 顯示：沒有標註的 OR 有標註且符合的
            if effective_domiciles:
                # 有標註，檢查是否符合使用者選擇的具體設籍地
                if not (other_domiciles & set(effective_domiciles)):
                    return False
            # 沒有標註的會通過（符合「不限/未明定」）
    
    # 就讀地檢查（精確匹配邏輯，支援多選）
    if filters.get("就讀地"):
        group_study_loc = extract_tags_from_group(group, "就讀地")
        excluded_study_loc = extract_excluded_tags_from_group(group, "就讀地")
        
        user_study_locs = filters["就讀地"]  # 這是一個列表
        user_study_locs_set = set(user_study_locs)
        excluded_set = set(excluded_study_loc)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_study_locs = user_study_locs_set - excluded_set
        if not non_excluded_study_locs:
            # 使用者選擇的所有就讀地都在排除列表中，不顯示
            return False
        
        # 2. 處理「不限/未明定」選項（OR 邏輯）
        has_undetermined = "不限/未明定" in user_study_locs_set
        other_study_locs = user_study_locs_set - {"不限/未明定"}
        
        # 將標註「不限」的獎學金視為未標註
        effective_study_locs = [s for s in group_study_loc if s != "不限"]
        
        # 情況 1: 只選「不限/未明定」
        if has_undetermined and not other_study_locs:
            # 只顯示沒有標註就讀地的獎學金（或只標註「不限」的）
            if effective_study_locs:
                return False
        # 情況 2: 只選具體就讀地（沒選「不限/未明定」）
        elif not has_undetermined and other_study_locs:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not effective_study_locs:
                return False
            if not (other_study_locs & set(effective_study_locs)):
                return False
        # 情況 3: 同時選「不限/未明定」和具體就讀地（OR 邏輯）
        elif has_undetermined and other_study_locs:
            # 顯示：沒有標註的 OR 有標註且符合的
            if effective_study_locs:
                # 有標註，檢查是否符合使用者選擇的具體就讀地
                if not (other_study_locs & set(effective_study_locs)):
                    return False
            # 沒有標註的會通過（符合「不限/未明定」）
    
    # 特殊身份檢查（精確匹配邏輯，支援多選）
    if filters.get("特殊身份"):
        group_special = extract_tags_from_group(group, "特殊身份")
        excluded_special = extract_excluded_tags_from_group(group, "特殊身份")
        
        user_special = filters["特殊身份"]  # 這是一個列表
        user_special_set = set(user_special)
        excluded_set = set(excluded_special)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_special = user_special_set - excluded_set
        if not non_excluded_special:
            # 使用者選擇的所有特殊身份都在排除列表中，不顯示
            return False
        
        # 2. 處理「未提及」選項（OR 邏輯）
        has_unmentioned = "未提及" in user_special_set
        other_special = user_special_set - {"未提及"}
        
        # 情況 1: 只選「未提及」
        if has_unmentioned and not other_special:
            # 只顯示沒有標註特殊身份的獎學金
            if group_special:
                return False
        # 情況 2: 只選具體特殊身份（沒選「未提及」）
        elif not has_unmentioned and other_special:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not group_special:
                return False
            if not (other_special & set(group_special)):
                return False
        # 情況 3: 同時選「未提及」和具體特殊身份（OR 邏輯）
        elif has_unmentioned and other_special:
            # 顯示：沒有標註的 OR 有標註且符合的
            if group_special:
                # 有標註，檢查是否符合使用者選擇的具體特殊身份
                if not (other_special & set(group_special)):
                    return False
            # 沒有標註的會通過（符合「未提及」）
    
    # 家庭境遇檢查（精確匹配邏輯，支援多選）
    if filters.get("家庭境遇"):
        group_family = extract_tags_from_group(group, "家庭境遇")
        excluded_family = extract_excluded_tags_from_group(group, "家庭境遇")
        
        user_family = filters["家庭境遇"]  # 這是一個列表
        user_family_set = set(user_family)
        excluded_set = set(excluded_family)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_family = user_family_set - excluded_set
        if not non_excluded_family:
            # 使用者選擇的所有家庭境遇都在排除列表中，不顯示
            return False
        
        # 2. 處理「未提及」選項（OR 邏輯）
        has_unmentioned = "未提及" in user_family_set
        other_family = user_family_set - {"未提及"}
        
        # 情況 1: 只選「未提及」
        if has_unmentioned and not other_family:
            # 只顯示沒有標註家庭境遇的獎學金
            if group_family:
                return False
        # 情況 2: 只選具體家庭境遇（沒選「未提及」）
        elif not has_unmentioned and other_family:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not group_family:
                return False
            if not (other_family & set(group_family)):
                return False
        # 情況 3: 同時選「未提及」和具體家庭境遇（OR 邏輯）
        elif has_unmentioned and other_family:
            # 顯示：沒有標註的 OR 有標註且符合的
            if group_family:
                # 有標註，檢查是否符合使用者選擇的具體家庭境遇
                if not (other_family & set(group_family)):
                    return False
            # 沒有標註的會通過（符合「未提及」）
    
    
    # 經濟相關證明檢查（精確匹配邏輯，支援多選）
    if filters.get("經濟相關證明"):
        group_economic = extract_tags_from_group(group, "經濟相關證明")
        excluded_economic = extract_excluded_tags_from_group(group, "經濟相關證明")
        
        user_economic = filters["經濟相關證明"]  # 這是一個列表
        user_economic_set = set(user_economic)
        excluded_set = set(excluded_economic)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_economic = user_economic_set - excluded_set
        if not non_excluded_economic:
            # 使用者選擇的所有經濟相關證明都在排除列表中，不顯示
            return False
        
        # 2. 處理「未提及」選項（OR 邏輯）
        has_unmentioned = "未提及" in user_economic_set
        other_economic = user_economic_set - {"未提及"}
        
        # 情況 1: 只選「未提及」
        if has_unmentioned and not other_economic:
            # 只顯示沒有標註經濟相關證明的獎學金
            if group_economic:
                return False
        # 情況 2: 只選具體經濟相關證明（沒選「未提及」）
        elif not has_unmentioned and other_economic:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not group_economic:
                return False
            if not (other_economic & set(group_economic)):
                return False
        # 情況 3: 同時選「未提及」和具體經濟相關證明（OR 邏輯）
        elif has_unmentioned and other_economic:
            # 顯示：沒有標註的 OR 有標註且符合的
            if group_economic:
                # 有標註，檢查是否符合使用者選擇的具體經濟相關證明
                if not (other_economic & set(group_economic)):
                    return False
            # 沒有標註的會通過（符合「未提及」）
    
    # 補助/獎學金排斥檢查（精確匹配邏輯，支援多選）
    if filters.get("補助/獎學金排斥"):
        group_exclusion = extract_tags_from_group(group, "補助/獎學金排斥")
        excluded_exclusion = extract_excluded_tags_from_group(group, "補助/獎學金排斥")
        
        user_exclusion = filters["補助/獎學金排斥"]  # 這是一個列表
        user_exclusion_set = set(user_exclusion)
        excluded_set = set(excluded_exclusion)
        
        # 1. 檢查排除條件（改進邏輯）
        non_excluded_exclusion = user_exclusion_set - excluded_set
        if not non_excluded_exclusion:
            # 使用者選擇的所有選項都在排除列表中，不顯示
            return False
        
        # 2. 處理「未提及」選項（OR 邏輯）
        has_unmentioned = "未提及" in user_exclusion_set
        other_exclusion = user_exclusion_set - {"未提及"}
        
        # 情況 1: 只選「未提及」
        if has_unmentioned and not other_exclusion:
            # 只顯示沒有標註補助/獎學金排斥的獎學金
            if group_exclusion:
                return False
        # 情況 2: 只選具體選項（沒選「未提及」）
        elif not has_unmentioned and other_exclusion:
            # 只顯示有標註且與使用者選擇有交集的獎學金
            if not group_exclusion:
                return False
            if not (other_exclusion & set(group_exclusion)):
                return False
        # 情況 3: 同時選「未提及」和具體選項（OR 邏輯）
        elif has_unmentioned and other_exclusion:
            # 顯示：沒有標註的 OR 有標註且符合的
            if group_exclusion:
                # 有標註，檢查是否符合使用者選擇的具體選項
                if not (other_exclusion & set(group_exclusion)):
                    return False
            # 沒有標註的會通過（符合「未提及」）
    
    
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
    # 關鍵字搜尋
    if filters.get("keyword"):
        keyword = filters["keyword"].lower()
        searchable_text = f"{scholarship.get('scholarship_name', '')} {scholarship.get('eligibility', '')}".lower()
        if keyword not in searchable_text:
            return False
    
    groups = scholarship.get("tags", {}).get("groups", [])
    common_tags = scholarship.get("tags", {}).get("common_tags", [])
    
    # 如果沒有 groups，使用 common_tags 建立 pseudo_group
    if not groups:
        pseudo_group = {"requirements": common_tags}
        return check_group_match(pseudo_group, filters)
    
    # 檢查每個 group（結合 common_tags）
    for group in groups:
        combined_group = {
            "requirements": group.get("requirements", []) + common_tags
        }
        if check_group_match(combined_group, filters):
            return True
    
    return False


# ==================== 金額與名額過濾 ====================

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

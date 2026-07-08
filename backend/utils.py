"""
货盘查询系统 - 工具函数
"""
import re
from datetime import datetime
from backend.config import STOCK_SUFFICIENT_THRESHOLD, STOCK_TENSE_THRESHOLD, PRICE_RANGES


def calc_stock_status(stock: int) -> str:
    """计算库存状态"""
    if stock is None:
        return "缺货"
    if stock > STOCK_SUFFICIENT_THRESHOLD:
        return "充足"
    elif stock >= STOCK_TENSE_THRESHOLD:
        return "紧张"
    else:
        return "缺货"


def calc_price_range(price_usd) -> str:
    """计算价格区间"""
    if price_usd is None:
        return None
    try:
        price = float(price_usd)
    except (TypeError, ValueError):
        return None

    for low, high, label in PRICE_RANGES:
        if low <= price < high:
            return label
    return None


def generate_batch_no() -> str:
    """生成导入批次号：IMP-YYYYMMDDHHmmss"""
    return f"IMP-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def extract_file_date(filename: str) -> str:
    """
    从文件名中提取日期
    例：'2026.6.22号美国仓库存表.xlsx' -> '2026.6.22'
        '幸色海外仓美国站2025年11月产品新报价.xlsx' -> '2025.11'
    """
    # 尝试匹配 2026.6.22 格式
    match = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', filename)
    if match:
        return f"{match.group(1)}.{match.group(2)}.{match.group(3)}"

    # 尝试匹配 2025年11月 格式
    match = re.search(r'(\d{4})年(\d{1,2})月', filename)
    if match:
        return f"{match.group(1)}.{match.group(2)}"

    # 尝试匹配 2025-11 格式
    match = re.search(r'(\d{4})-(\d{1,2})', filename)
    if match:
        return f"{match.group(1)}.{match.group(2)}"

    return datetime.now().strftime("%Y.%m.%d")


def is_newer_date(date_str1: str, date_str2: str) -> bool:
    """判断 date_str1 是否比 date_str2 更新"""
    try:
        # 统一转换为可比较的格式
        parts1 = [int(p) for p in date_str1.split(".")]
        parts2 = [int(p) for p in date_str2.split(".")]
        # 补齐长度
        while len(parts1) < 3:
            parts1.append(0)
        while len(parts2) < 3:
            parts2.append(0)
        return parts1 > parts2
    except (ValueError, AttributeError):
        return False

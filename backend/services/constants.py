"""
共享业务常量 — 统一管理避免多处定义不一致。
"""

# 电费单价（元/度），用于：抄表计算、退房验收电费扣款、账单生成
ELECTRICITY_RATE = 1.2  # yuan/kWh

# 北京时区（UTC+8），所有时间计算必须使用此常量，禁止依赖服务器本地时间
from datetime import timezone, timedelta, datetime
BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> datetime:
    """返回北京时间 datetime 对象。"""
    return datetime.now(BEIJING_TZ)


def beijing_now_str() -> str:
    """返回北京时间字符串 YYYY-MM-DD HH:MM:SS。"""
    return beijing_now().strftime("%Y-%m-%d %H:%M:%S")


def beijing_today_str() -> str:
    """返回北京时间今天日期 YYYY-MM-DD，用于逾期判断等日期比较。"""
    return beijing_now().strftime("%Y-%m-%d")

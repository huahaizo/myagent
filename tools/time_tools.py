
from agents import function_tool
from datetime import datetime

@function_tool
def now_date() -> str:
    """这是返回当前年月日的函数"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d")
@function_tool
def now_time() -> str:
    """这是返回当前时间的函数"""
    now = datetime.now()
    return now.strftime("%H:%M:%S")

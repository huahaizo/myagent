from agents import function_tool
from datetime import datetime
#
# def add(a,b):
#     return a + b
#
# 这是普通函数的写法

"""
添加装饰后变成agent可调用的函数

int则是说明数据类型
-> 是为了说明输出的类型
"""

@function_tool
def add(a:int,b:int) -> int:
    """这是加法函数"""
    return a+b

@function_tool
def sub(a:int,b:int) -> int:
    """这是减法函数，可以返回a-b的值"""
    return a-b




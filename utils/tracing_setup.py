
"""
My Agent Tracing 初始化。

只使用本地处理器，
不使用 SDK 默认的外部追踪导出处理器。
"""

from agents import tracing

from utils.trace_monitor import LocalTraceProcessor


_initialized = False


def setup_tracing():
    global _initialized

    if _initialized:
        return

    # 替换默认处理器列表
    tracing.set_trace_processors([
        LocalTraceProcessor()
    ])

    _initialized = True

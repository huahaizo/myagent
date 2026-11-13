
"""
保存当前任务的追踪信息。

ContextVar 适用于 asyncio 异步任务。
"""

from contextvars import ContextVar

# 当前任务的追踪 ID
task_id_var = ContextVar(
    "task_id",
    default="-"
)


def get_task_id() -> str:
    """获取当前任务 ID。"""
    return task_id_var.get()

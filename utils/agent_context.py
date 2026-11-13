
"""
My Agent 运行上下文。

用于保存一次 Agent 运行所需的应用数据。

注意：
这不是聊天历史，也不是模型提示词。
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class MyAgentContext:
    """My Agent 的运行上下文。"""

    session_id: str

    workspace_dir: Path

    # 当前任务是否允许申请文件写入。
    # 实际写入仍必须经过 GUI 用户确认。
    allow_file_write: bool = False

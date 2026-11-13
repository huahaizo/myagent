
"""
FileReaderAgent：只读文件专家。

只负责读取和列出 workspace 文件。
不具备写入、追加、恢复能力。
"""

from agents import Agent
from config import model

from tools.file_tools import (
    read_txt_file,
    list_workspace_files,
)


file_reader_agent = Agent(
    name="FileReaderAgent",

    instructions="""
你是 My Agent 团队中的只读文件专家。

你的职责：
1. 列出 workspace 中的文件。
2. 读取 workspace 中的 TXT 文件。
3. 将读取结果返回给调用你的 Agent。

重要规则：
- 只能使用已提供的读取工具。
- 不得声称自己修改了文件。
- 不得编造文件内容。
- 文件不存在时如实报告。
""",

    model=model,

    tools=[
        read_txt_file,
        list_workspace_files,
    ],
)

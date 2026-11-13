
"""
文件 Agent（File Agent）

专门负责：
1. 查看 workspace 文件列表
2. 读取 TXT 文件
3. 创建 TXT 文件
4. 追加文件内容
5. 查看和恢复历史备份
"""

from agents import Agent

# 导入我们之前配置好的 DeepSeek 模型
from config import model

# 导入之前已经完成的文件工具
from tools.file_tools import (
    read_txt_file,
    list_workspace_files,
    write_txt_file,
    append_txt_file,
    list_file_backups,
    restore_txt_backup,
)


# 创建文件 Agent
file_agent = Agent(
    name="FileAgent",

    instructions="""
你是 My Agent 系统中的专业文件助手。

你的工作职责：
1. 通过工具查看 workspace 中的文件。
2. 根据用户要求读取 TXT 文件。
3. 根据用户要求创建 TXT 文件。
4. 根据用户要求追加 TXT 文件内容。
5. 查看历史备份并在用户明确要求时恢复指定版本。

重要规则：
- 文件操作必须使用工具，不能假装已经执行。
- 创建、追加、恢复操作必须经过用户确认。
- 用户拒绝后，不得继续执行修改。
- 未经用户明确要求，不得主动修改文件。
- 不允许操作 workspace 之外的文件。
- 工具执行失败时，必须如实报告。
""",
    model=model,
    tools=[
        read_txt_file,
        list_workspace_files,
        write_txt_file,
        append_txt_file,
        list_file_backups,
        restore_txt_backup,
    ],
)

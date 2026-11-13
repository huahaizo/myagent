
"""
MainAgent：My Agent 主协调员。

使用官方：
- Agent
- Agent.as_tool()
- Handoffs
"""

from agents import Agent

from config import model

from tools.time_tools import now_date, now_time

from multi_agents.file_agent import file_agent
from multi_agents.code_agent import code_agent
from multi_agents.search_agent import search_agent

main_agent = Agent(
    name="MainAgent",

    instructions="""
你是 My Agent 的主协调员。

你的任务是理解用户需求，并协调专业 Agent。

协作规则：

1. 普通聊天和简单问题：
   直接回答。

2. 日期和时间：
   使用 now_date 或 now_time。

3. 文件管理任务：
   交给 FileAgent。
   修改、追加或恢复文件时必须遵守现有用户确认机制。

4. Python 编程任务：
   使用 ask_code_agent 请求 CodeAgent 协助。

5. 需要文件内容的编程任务：
   优先使用 ask_code_agent。
   CodeAgent 可以进一步调用只读 FileReaderAgent。

6. 需要文件管理与编程专家共同参与的任务：
   可以分别调用 ask_file_agent 和 ask_code_agent，
   再综合两者结果。

7. 不得编造文件内容或工具执行结果。
8. 网络搜索任务：
   当用户询问最新消息、实时信息、
   技术文档或需要外部事实验证的问题时，
   使用 ask_search_agent。

   不得编造搜索结果和来源链接。
优先使用中文回答。
""",

    model=model,

    tools=[
        now_date,
        now_time,

        code_agent.as_tool(
            tool_name="ask_code_agent",
            tool_description=(
                "调用 Python 编程专家，"
                "分析代码、解决编程问题，"
                "必要时协作读取 workspace 文件。"
            )
        ),search_agent.as_tool(
         tool_name="ask_search_agent",
        tool_description=(
            "调用联网搜索专家，"
        "搜索最新信息、技术文档、新闻和公开资料。"
         )
        ),

        file_agent.as_tool(
            tool_name="ask_file_agent",
            tool_description=(
                "调用文件管理专家，处理 workspace "
                "文件的读取、列出及管理任务。"
            )
        ),

    ],

    handoffs=[
        file_agent,
    ],
)

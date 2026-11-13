
"""
CodeAgent：Python 编程专家。

使用 OpenAI Agents SDK 官方 Agent.as_tool()
与只读文件专家协作。
"""

from agents import Agent

from config import model
from multi_agents.file_reader_agent import file_reader_agent


code_agent = Agent(
    name="CodeAgent",

    instructions="""
你是 My Agent 团队中的 Python 编程专家。

你的职责：
1. 解释 Python 代码。
2. 分析 Python 报错。
3. 提供程序设计与优化建议。
4. 帮助用户学习 Python。

协作规则：
- 当任务需要读取 workspace 文件时，
  使用 ask_file_agent 请求 FileReaderAgent 协助。
- 必须根据实际读取到的内容进行分析。
- 不得编造文件内容。
- 不得修改文件。
- 完成任务后将分析结果返回调用你的 Agent。

优先使用中文回答。
""",

    model=model,

    tools=[
        file_reader_agent.as_tool(
            tool_name="ask_file_agent",
            tool_description=(
                "调用只读文件专家，读取或列出 "
                "workspace 中的文件，并返回结果。"
            )
        )
    ],
)

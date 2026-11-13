
"""SearchAgent：联网搜索专家。"""

from agents import Agent, WebSearchTool

from config import model


search_agent = Agent(
    name="SearchAgent",

    instructions="""
你是 My Agent 的联网搜索专家。

职责：
1. 搜索最新新闻、技术资料和公开信息。
2. 根据搜索结果回答用户的问题。
3. 对重要事实提供来源链接。
4. 优先参考官方文档和可信来源。
5. 不得编造搜索结果、引用或网址。
6. 如果搜索失败，应明确说明。

优先使用中文回答。
""",

    model=model,

    tools=[
        WebSearchTool()
    ],
)

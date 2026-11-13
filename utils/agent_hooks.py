
"""
My Agent 运行事件日志

基于 OpenAI Agents SDK 官方 RunHooks。

职责：
1. 记录 Agent 启动
2. 记录 Agent 结束
3. 记录 Agent Handoff
4. 记录工具开始
5. 记录工具结束

调用链和耗时统计将交给官方 Tracing。

不记录用户消息、工具参数、文件内容或 API Key。
"""

from agents import RunHooks

from utils.logger import logger
from utils.task_context import get_task_id


class MyAgentHooks(RunHooks):
    """
    My Agent 自定义运行事件处理器。
    """

    async def on_agent_start(
        self,
        context,
        agent
    ):
        """Agent 开始执行。"""

        logger.info(
            "[Task=%s] [Agent启动] %s",
            get_task_id(),
            agent.name
        )

    async def on_agent_end(
        self,
        context,
        agent,
        output
    ):
        """Agent 完成执行。"""

        logger.info(
            "[Task=%s] [Agent结束] %s",
            get_task_id(),
            agent.name
        )

    async def on_handoff(
        self,
        context,
        from_agent,
        to_agent
    ):
        """Agent 发生 Handoff。"""

        logger.info(
            "[Task=%s] [Agent交接] %s -> %s",
            get_task_id(),
            from_agent.name,
            to_agent.name
        )

    async def on_tool_start(
        self,
        context,
        agent,
        tool
    ):
        """工具开始执行。"""

        logger.info(
            "[Task=%s] [工具开始] Agent=%s | Tool=%s",
            get_task_id(),
            agent.name,
            tool.name
        )

    async def on_tool_end(
        self,
        context,
        agent,
        tool,
        result
    ):
        """工具返回结果。"""

        logger.info(
            "[Task=%s] [工具结束] Agent=%s | Tool=%s",
            get_task_id(),
            agent.name,
            tool.name
        )

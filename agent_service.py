
"""My Agent 服务层：Token 智能压缩版。"""

import time
import uuid
from pathlib import Path

from agents import Runner

from multi_agents.main_agent import main_agent
from utils.agent_hooks import MyAgentHooks
from utils.compacting_session import CompactingSession
from utils.logger import logger
from utils.task_context import task_id_var


PROJECT_DIR = Path(__file__).resolve().parent

HISTORY_DIR = PROJECT_DIR / "history"
HISTORY_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_PATH = str(
    HISTORY_DIR / "chat_history.db"
)

SUMMARY_DIR = HISTORY_DIR / "summaries"


# 正式使用的初始预算。
# 这些是估算 Token，不是模型的真实上限。
TRIGGER_TOKENS = 6000
KEEP_RECENT_TOKENS = 2000


def create_session(session_id: str):
    """创建带压缩能力的 SDK Session。"""

    return CompactingSession(
        session_id=session_id,
        db_path=DATABASE_PATH,
        summary_dir=SUMMARY_DIR,
        trigger_tokens=TRIGGER_TOKENS,
        keep_recent_tokens=KEEP_RECENT_TOKENS,
    )


def get_tool_name(item):
    """从 SDK 事件中获取工具名称。"""

    raw_item = getattr(
        item,
        "raw_item",
        None,
    )

    if raw_item is None:
        return "unknown"

    function = getattr(
        raw_item,
        "function",
        None,
    )

    if function is not None:
        name = getattr(
            function,
            "name",
            None,
        )

        if name:
            return name

    return (
        getattr(raw_item, "name", None)
        or "unknown"
    )


def log_agent_events(result):
    """记录 SDK 事件，不保存聊天正文。"""

    for item in result.new_items:
        item_type = getattr(
            item,
            "type",
            "",
        )

        agent = getattr(
            item,
            "agent",
            None,
        )

        agent_name = getattr(
            agent,
            "name",
            "unknown",
        )

        if item_type == "handoff_call_item":
            logger.info(
                "[Agent交接调用] Agent=%s",
                agent_name,
            )

        elif item_type == "handoff_output_item":
            logger.info(
                "[Agent交接完成] Agent=%s",
                agent_name,
            )

        elif item_type == "tool_call_item":
            logger.info(
                "[工具调用] Agent=%s | Tool=%s",
                agent_name,
                get_tool_name(item),
            )

        elif item_type == "tool_call_output_item":
            logger.info(
                "[工具结果] Agent=%s",
                agent_name,
            )

        elif item_type == "message_output_item":
            logger.info(
                "[消息生成] Agent=%s",
                agent_name,
            )


async def ask_agent(
    message: str,
    session_id: str,
) -> str:
    """GUI 聊天入口。"""

    task_id = uuid.uuid4().hex[:12]
    token = task_id_var.set(task_id)

    start_time = time.perf_counter()

    try:
        session = create_session(session_id)

        logger.info(
            "[Task=%s] [任务开始] "
            "Session=%s | Agent=%s",
            task_id,
            session_id,
            main_agent.name,
        )

        # 先准备压缩上下文。
        await session.prepare()

        # 交给官方 SDK 执行。
        result = await Runner.run(
            starting_agent=main_agent,
            input=message,
            session=session,
            hooks=MyAgentHooks(),
        )

        log_agent_events(result)

        elapsed = (
            time.perf_counter() - start_time
        )

        logger.info(
            "[Task=%s] [任务完成] "
            "FinalAgent=%s | 耗时=%.2f秒",
            task_id,
            result.last_agent.name,
            elapsed,
        )

        if result.final_output is None:
            return ""

        return str(result.final_output)

    except Exception:
        logger.exception(
            "[Task=%s] [任务失败]",
            task_id,
        )
        raise

    finally:
        task_id_var.reset(token)


async def delete_agent_session(
    session_id: str,
):
    """清空会话及对应摘要。"""

    session = create_session(session_id)

    await session.clear_session()

    logger.info(
        "[会话清空] Session=%s",
        session_id,
    )

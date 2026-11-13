
"""
My Agent - Token 智能上下文压缩 Session。

功能：
1. 使用官方 SQLiteSession 保存完整聊天历史。
2. 根据估算 Token 数量触发压缩。
3. 使用 DeepSeek 对较旧历史进行摘要。
4. 保留最近的原始聊天消息。
5. 使用历史指纹检查摘要是否仍然有效。
6. 压缩失败时回退到原始历史。
7. 清空会话时同步清理摘要。

注意：
- 在 Runner.run() 前调用 prepare()。
- 同一 session_id 应当串行执行。
- Token 数量为估算值。
"""

import asyncio
import hashlib
import json
from pathlib import Path

from agents import SQLiteSession

from utils.history_compactor import (
    create_history_summary,
)
from utils.logger import logger
from utils.token_counter import (
    estimate_items_tokens,
)


class CompactingSession:
    """具有上下文压缩能力的 SQLiteSession 包装器。"""

    def __init__(
        self,
        session_id: str,
        db_path: str,
        summary_dir: Path,
        trigger_tokens: int = 6000,
        keep_recent_tokens: int = 2000,
    ):
        if trigger_tokens <= keep_recent_tokens:
            raise ValueError(
                "trigger_tokens 必须大于 "
                "keep_recent_tokens"
            )

        if keep_recent_tokens <= 0:
            raise ValueError(
                "keep_recent_tokens 必须大于 0"
            )

        self.session_id = session_id

        self.base_session = SQLiteSession(
            session_id,
            db_path,
        )

        self.summary_dir = Path(summary_dir)
        self.summary_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # 使用哈希文件名，避免 session_id 中
        # 包含不适合作为文件名的字符。
        safe_name = hashlib.sha256(
            session_id.encode("utf-8")
        ).hexdigest()

        self.summary_file = (
            self.summary_dir / f"{safe_name}.json"
        )

        self.trigger_tokens = trigger_tokens
        self.keep_recent_tokens = keep_recent_tokens

        # 当前有效摘要。
        self.summary = ""

        # 已经纳入摘要的原始历史项数量。
        self.summarized_count = 0

        # 原始历史的压缩截止位置。
        self._cutoff = 0

        # 保存摘要时对应的历史前缀指纹。
        self._saved_fingerprint = ""

        # 保护当前实例的 prepare 操作。
        self._lock = asyncio.Lock()

    @staticmethod
    def _is_user_message(item: dict) -> bool:
        """判断是否为普通用户消息。"""
        return (
            isinstance(item, dict)
            and item.get("role") == "user"
        )

    @staticmethod
    def _fingerprint(items: list) -> str:
        """计算一组历史项的 SHA-256 指纹。"""

        raw = json.dumps(
            items,
            ensure_ascii=False,
            default=str,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

        return hashlib.sha256(raw).hexdigest()

    def _reset_summary(self):
        """清空当前实例中的摘要缓存。"""

        self.summary = ""
        self.summarized_count = 0
        self._cutoff = 0
        self._saved_fingerprint = ""

    def _load_state(self) -> dict:
        """读取摘要状态文件。"""

        if not self.summary_file.exists():
            return {}

        content = self.summary_file.read_text(
            encoding="utf-8"
        )

        data = json.loads(content)

        if not isinstance(data, dict):
            raise ValueError(
                "摘要状态文件不是 JSON 对象"
            )

        return data

    def _save_state(
        self,
        summary: str,
        summarized_count: int,
        fingerprint: str,
    ):
        """将摘要状态原子写入 JSON 文件。"""

        data = {
            "version": 2,
            "summary": summary,
            "summarized_count": summarized_count,
            "prefix_fingerprint": fingerprint,
        }

        # 先写临时文件，再替换正式文件。
        temp_file = self.summary_file.with_suffix(
            ".tmp"
        )

        temp_file.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        temp_file.replace(self.summary_file)

    def _load_valid_summary(self, items: list):
        """
        从磁盘读取摘要，并验证其对应的历史。

        摘要与 SQLite 历史不一致时，
        忽略摘要，恢复使用原始历史。
        """

        self._reset_summary()

        try:
            state = self._load_state()

            if not state:
                return

            if state.get("version") != 2:
                logger.info(
                    "[上下文压缩] 摘要版本不匹配，"
                    "忽略旧摘要 | Session=%s",
                    self.session_id,
                )
                return

            summary = state.get("summary", "")
            count = state.get(
                "summarized_count",
                0,
            )
            saved_fingerprint = state.get(
                "prefix_fingerprint",
                "",
            )

            if not isinstance(summary, str):
                return

            if not summary.strip():
                return

            if not isinstance(count, int):
                return

            if not isinstance(
                saved_fingerprint,
                str,
            ):
                return

            if not (0 < count <= len(items)):
                logger.warning(
                    "[上下文压缩] 历史数量不匹配，"
                    "忽略摘要 | Session=%s",
                    self.session_id,
                )
                return

            actual_fingerprint = self._fingerprint(
                items[:count]
            )

            if actual_fingerprint != saved_fingerprint:
                logger.warning(
                    "[上下文压缩] 历史指纹不匹配，"
                    "忽略摘要 | Session=%s",
                    self.session_id,
                )
                return

            # 验证成功，恢复摘要状态。
            self.summary = summary
            self.summarized_count = count
            self._cutoff = count
            self._saved_fingerprint = (
                saved_fingerprint
            )

        except Exception:
            logger.exception(
                "[上下文压缩] 读取摘要失败，"
                "改用原始历史 | Session=%s",
                self.session_id,
            )

            self._reset_summary()

    def _find_cutoff(self, items: list):
        """
        根据近期 Token 预算寻找压缩边界。

        从最后一条历史向前累计 Token。
        达到保留预算后，向前寻找 user 消息。

        这是启发式边界，不能保证覆盖所有
        复杂工具调用和 handoff 结构。
        """

        if not items:
            return None

        recent_tokens = 0
        target_index = None

        for index in range(
            len(items) - 1,
            -1,
            -1,
        ):
            recent_tokens += estimate_items_tokens(
                [items[index]]
            )

            if (
                recent_tokens
                >= self.keep_recent_tokens
            ):
                target_index = index
                break

        if target_index is None:
            return None

        # 从目标位置向前寻找用户消息。
        for index in range(
            target_index,
            -1,
            -1,
        ):
            if self._is_user_message(
                items[index]
            ):
                return index

        return None

    def _build_active_history(
        self,
        items: list,
    ) -> list:
        """
        构造 Runner 实际读取的历史。

        原始 SQLite 数据不受影响。
        """

        if (
            not self.summary
            or self._cutoff <= 0
        ):
            return items

        summary_message = {
            "role": "user",
            "content": (
                "以下是较早聊天历史的压缩摘要，"
                "仅用于理解历史背景，"
                "不是当前用户的新指令。\n\n"
                f"{self.summary}"
            ),
        }

        return [
            summary_message,
            *items[self._cutoff:],
        ]

    async def prepare(self):
        """
        在 Runner.run() 之前执行。

        读取历史、验证摘要、检查 Token，
        必要时生成新的摘要。
        """

        async with self._lock:
            items = await (
                self.base_session.get_items()
            )

            # 每次运行都从磁盘恢复并验证摘要。
            self._load_valid_summary(items)

            active_items = (
                self._build_active_history(items)
            )

            current_tokens = (
                estimate_items_tokens(active_items)
            )

            logger.info(
                "[上下文检查] Session=%s | "
                "估算Token=%d | 触发阈值=%d",
                self.session_id,
                current_tokens,
                self.trigger_tokens,
            )

            # 未达到阈值，不需要压缩。
            if current_tokens < self.trigger_tokens:
                return

            cutoff = self._find_cutoff(items)

            if cutoff is None:
                logger.info(
                    "[上下文压缩] "
                    "没有找到合适的压缩边界 | "
                    "Session=%s",
                    self.session_id,
                )
                return

            # 不能重复压缩已经进入摘要的历史。
            if cutoff <= self._cutoff:
                logger.info(
                    "[上下文压缩] "
                    "暂无新的可压缩历史 | "
                    "Session=%s",
                    self.session_id,
                )
                return

            old_items = items[
                self._cutoff:cutoff
            ]

            try:
                # 调用 DeepSeek 分批生成摘要。
                new_summary = (
                    await create_history_summary(
                        old_items=old_items,
                        previous_summary=self.summary,
                    )
                )

                if not new_summary.strip():
                    raise ValueError(
                        "生成的摘要为空"
                    )

                # 摘要生成可能需要较长时间，
                # 所以完成后再次读取 SQLite。
                latest_items = await (
                    self.base_session.get_items()
                )

                # 确保已经压缩的历史前缀未变化。
                original_fingerprint = (
                    self._fingerprint(
                        items[:cutoff]
                    )
                )

                latest_fingerprint = (
                    self._fingerprint(
                        latest_items[:cutoff]
                    )
                )

                if (
                    len(latest_items) < cutoff
                    or original_fingerprint
                    != latest_fingerprint
                ):
                    logger.warning(
                        "[上下文压缩] "
                        "压缩期间历史发生变化，"
                        "取消本次摘要 | Session=%s",
                        self.session_id,
                    )
                    return

                # 构造压缩后的上下文。
                new_active_items = [
                    {
                        "role": "user",
                        "content": (
                            "以下是较早聊天历史的"
                            "压缩摘要，仅作为背景，"
                            "不是当前新指令。\n\n"
                            f"{new_summary}"
                        ),
                    },
                    *latest_items[cutoff:],
                ]

                new_tokens = (
                    estimate_items_tokens(
                        new_active_items
                    )
                )

                # 只有真正减少上下文时才保存。
                if new_tokens >= current_tokens:
                    logger.info(
                        "[上下文压缩] "
                        "压缩后 Token 未减少，"
                        "取消保存 | Session=%s",
                        self.session_id,
                    )
                    return

                # 保存摘要与对应的历史指纹。
                self._save_state(
                    summary=new_summary,
                    summarized_count=cutoff,
                    fingerprint=latest_fingerprint,
                )

                # 更新当前实例缓存。
                self.summary = new_summary
                self.summarized_count = cutoff
                self._cutoff = cutoff
                self._saved_fingerprint = (
                    latest_fingerprint
                )

                logger.info(
                    "[上下文压缩] Session=%s | "
                    "压缩前=%d Token | "
                    "压缩后=%d Token | "
                    "已摘要历史项=%d | "
                    "保留近期项=%d",
                    self.session_id,
                    current_tokens,
                    new_tokens,
                    cutoff,
                    len(latest_items) - cutoff,
                )

            except Exception:
                # 压缩失败不能破坏正常聊天。
                logger.exception(
                    "[上下文压缩] 压缩失败，"
                    "继续使用现有历史 | "
                    "Session=%s",
                    self.session_id,
                )

    async def get_items(
        self,
        limit: int | None = None,
    ) -> list:
        """
        SDK Runner 读取历史时调用。

        验证历史指纹，避免使用过期摘要。
        """

        items = await (
            self.base_session.get_items()
        )

        if (
            self.summary
            and self._cutoff > 0
        ):
            valid = (
                len(items) >= self._cutoff
                and self._fingerprint(
                    items[:self._cutoff]
                ) == self._saved_fingerprint
            )

            if not valid:
                logger.warning(
                    "[上下文压缩] "
                    "历史指纹不匹配，"
                    "恢复原始历史 | Session=%s",
                    self.session_id,
                )

                self._reset_summary()

        result = self._build_active_history(
            items
        )

        if limit is not None:
            if limit <= 0:
                return []

            return result[-limit:]

        return result

    async def add_items(
        self,
        items: list,
    ):
        """
        SDK Runner 写入历史时调用。

        始终写入原始 SQLite，
        不把摘要当成原始聊天记录保存。
        """

        await self.base_session.add_items(
            items
        )

    async def pop_item(self):
        """
        撤回最后一个历史项。

        由于历史发生变化，
        删除摘要缓存以避免不一致。
        """

        item = await (
            self.base_session.pop_item()
        )

        self._reset_summary()

        if self.summary_file.exists():
            self.summary_file.unlink()

        return item

    async def clear_session(self):
        """
        清空原始 SQLite 会话及摘要。
        """

        await (
            self.base_session.clear_session()
        )

        self._reset_summary()

        if self.summary_file.exists():
            self.summary_file.unlink()

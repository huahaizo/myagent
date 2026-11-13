
"""
My Agent 本地 Tracing 处理器。

基于 OpenAI Agents SDK 官方 Tracing。

只记录：
- Trace ID
- Span ID
- Parent Span ID
- Span 类型
- 开始和结束时间

不记录模型输入、输出、工具参数或文件正文。
"""

from datetime import datetime

from utils.logger import logger


class LocalTraceProcessor:

    def on_trace_start(self, trace):
        logger.info(
            "[Trace开始] Trace=%s",
            getattr(trace, "trace_id", "-")
        )

    def on_trace_end(self, trace):
        logger.info(
            "[Trace结束] Trace=%s",
            getattr(trace, "trace_id", "-")
        )

    def on_span_start(self, span):
        span_data = getattr(span, "span_data", None)

        logger.info(
            "[Span开始] Span=%s | Parent=%s | Type=%s",
            getattr(span, "span_id", "-"),
            getattr(span, "parent_id", "-"),
            getattr(span_data, "type", "-")
        )

    def on_span_end(self, span):
        started_at = getattr(
            span,
            "started_at",
            None
        )

        ended_at = getattr(
            span,
            "ended_at",
            None
        )

        elapsed = None

        if started_at and ended_at:
            try:
                start = datetime.fromisoformat(
                    started_at.replace("Z", "+00:00")
                )

                end = datetime.fromisoformat(
                    ended_at.replace("Z", "+00:00")
                )

                elapsed = (
                    end - start
                ).total_seconds()

            except (ValueError, TypeError):
                pass

        logger.info(
            "[Span结束] Span=%s | 耗时=%s秒",
            getattr(span, "span_id", "-"),
            (
                f"{elapsed:.3f}"
                if elapsed is not None
                else "未知"
            )
        )

    def shutdown(self):
        pass

    def force_flush(self):
        pass

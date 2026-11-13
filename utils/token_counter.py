
"""估算聊天消息的 Token 数量。"""

import json


def estimate_text_tokens(text: str) -> int:
    """
    粗略估算 Token。

    中文通常每个字可能占多个 Token，
    英文、代码和 JSON 的比例也不同。

    使用偏保守的估算方式，
    避免把字符数直接当成 Token 数。
    """
    if not text:
        return 0

    return max(
        1,
        (len(text.encode("utf-8")) + 1) // 2,
    )


def estimate_items_tokens(items: list) -> int:
    """估算 SDK 历史消息的 Token 总量。"""

    total = 0

    for item in items:
        content = json.dumps(
            item,
            ensure_ascii=False,
            default=str,
        )

        total += estimate_text_tokens(content)

        # 额外预留消息结构开销。
        total += 12

    return total

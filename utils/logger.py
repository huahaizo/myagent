
"""
My Agent 统一日志系统。

功能：
1. 自动创建 logs 文件夹
2. 同时输出到控制台和日志文件
3. 记录时间、日志级别和内容
4. 自动轮换日志，避免文件无限增长
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


# 项目根目录
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 日志文件夹
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 日志文件路径
LOG_FILE = LOG_DIR / "agent.log"


def get_logger():
    """创建或获取统一日志对象。"""

    logger = logging.getLogger("MyAgent")

    # 避免重复添加 Handler，造成日志重复
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 写入文件：最大 5 MB，保留 3 个旧日志
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # 同时输出到 PyCharm 控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 避免向根 Logger 重复传播
    logger.propagate = False

    return logger


logger = get_logger()

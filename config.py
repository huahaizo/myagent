
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pathlib import Path
from agents import (
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)
# 加载 .env 文件
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# 从环境变量读取 DeepSeek API Key
DEEPSEEK_API_KEY = os.getenv("api_key")

# 关闭 OpenAI 云端追踪
set_tracing_disabled(True)
# 创建 DeepSeek 客户端
deepseek_client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
)

# 创建可复用的模型适配器
model = OpenAIChatCompletionsModel(
    model="deepseek-chat",
    openai_client=deepseek_client,
)
# 安全关闭网络客户端
async def close_ai_client():
    await deepseek_client.close()

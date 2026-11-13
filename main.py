import asyncio
from agents import Agent,Runner
from config import model
from tools.time_tools import now_date, now_time
from pathlib import Path
from agents import Agent, Runner, SQLiteSession


history_dir = Path(__file__).resolve().parent / "history"
history_dir.mkdir(parents=True, exist_ok=True)



agent = Agent(
    name="agent",
    instructions="""
    你是一个有用的助手     
    """,
    model=model,
    tools=[now_date, now_time]
)


async def main():
    session = SQLiteSession(
        "my_chat",
        str(history_dir / "chat_history.db")
    )
    while True:
        user_input = input("\n你：").strip()
        if user_input.lower() in ["exit", "quit", "退出"]:
            print("聊天结束")
            break
        if not user_input:
            continue
        result = await Runner.run(
            starting_agent=agent,
            input=user_input,
            session=session,
        )

        print("AI：", result.final_output)

if __name__ == '__main__':
    asyncio.run(main())

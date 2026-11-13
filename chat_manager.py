
import uuid
import json
from pathlib import Path

class ChatManager:

    def __init__(self):
        # 用字典保存所有聊天会话
        self.chats = {}

        # 记录当前选中的会话 ID
        self.current_chat_id = None
        # 获取项目根目录
        project_dir = Path(__file__).resolve().parent

        # 确保 history 文件夹存在
        history_dir = project_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)

        # 聊天列表保存的位置
        self.save_path = history_dir / "chats.json"
        self.load_chats()

    def save_chats(self):
        # 把会话字典写入 JSON 文件
        with open(self.save_path, "w", encoding="utf-8") as file:
            json.dump(
                self.chats,
                file,
                ensure_ascii=False,
                indent=4
            )

    def load_chats(self):
        # 如果文件不存在，就不需要加载
        if not self.save_path.exists():
            return

        # 从 JSON 文件读取历史会话
        with open(self.save_path, "r", encoding="utf-8") as file:
            self.chats = json.load(file)

    def update_title(self, chat_id, title):
        # 限制标题长度，避免左侧显示过长
        title = title.strip()[:20]

        # 修改指定会话的标题
        self.chats[chat_id]["title"] = title

        # 保存到 JSON 文件
        self.save_chats()

    def delete_chat(self, chat_id):
        # 如果会话不存在，就不进行删除
        if chat_id not in self.chats:
            return False

        # 从字典中删除指定会话
        del self.chats[chat_id]

        # 将修改后的会话列表保存到 JSON
        self.save_chats()

        return True

    def create_chat(self):
        # 生成唯一的会话 ID
        chat_id = uuid.uuid4().hex

        # 保存新会话的信息
        self.chats[chat_id] = {
            "title": "新聊天",
            "messages": []
        }

        # 将新会话设置为当前会话
        self.current_chat_id = chat_id
        self.save_chats()

        return chat_id

    def add_message(self, chat_id, sender, content):
        # 找到指定会话并添加消息
        self.chats[chat_id]["messages"].append({
            "sender": sender,
            "content": content
        })
        self.save_chats()

    def get_messages(self, chat_id):
        # 获取指定会话的所有消息
        return self.chats[chat_id]["messages"]
if __name__ == "__main__":
    manager = ChatManager()

    chat1 = manager.create_chat()
    manager.add_message(chat1, "user", "你好")

    chat2 = manager.create_chat()
    manager.add_message(chat2, "user", "我在学习 Python")

    print("会话1：", manager.get_messages(chat1))
    print("会话2：", manager.get_messages(chat2))
    print("保存位置：", manager.save_path)
    print("文件是否存在：", manager.save_path.exists())
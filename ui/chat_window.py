import asyncio
import threading
import queue
import traceback
import customtkinter as ctk
from chat_manager import ChatManager
from agent_service import ask_agent, delete_agent_session
from tools.file_tools import set_approval_queue
from ui import theme
from ui.chat_area import ChatArea
from ui.input_area import InputArea
from tkinter import messagebox
from config import close_ai_client
def start_ui():

    # ========================================
    # 1. 初始化窗口
    # ========================================

    ctk.set_appearance_mode("light")

    window = ctk.CTk()
    window.title("My Agent")

    window.geometry(
        f"{theme.WINDOW_WIDTH}x{theme.WINDOW_HEIGHT}"
    )
    window.minsize(850, 550)

    # ========================================
    # 2. 创建左右布局
    # ========================================

    # 左侧边栏
    sidebar = ctk.CTkFrame(
        window,
        width=theme.SIDEBAR_WIDTH,
        corner_radius=0,
        fg_color=theme.SIDEBAR_BG
    )
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)

    # 右侧聊天区域
    chat_area = ctk.CTkFrame(
        window,
        corner_radius=0,
        fg_color=theme.BACKGROUND
    )
    chat_area.pack(
        side="right",
        fill="both",
        expand=True
    )

    # ========================================
    # 3. 左侧标题
    # ========================================

    title = ctk.CTkLabel(
        sidebar,
        text="✦ My Agent",
        font=(theme.FONT_FAMILY, 20, "bold"),
        text_color=theme.TEXT_PRIMARY
    )
    title.pack(pady=(30, 20))

    # ========================================
    # 4. 创建聊天消息区域
    # ========================================

    chat = ChatArea(chat_area)
    chat.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=(10, 0)
    )

    # ========================================
    # 5. 初始化聊天管理器
    # ========================================

    # ChatManager 会自动读取 chats.json
    manager = ChatManager()

    # 如果存在历史聊天，恢复最后创建的会话
    if manager.chats:
        current_session_id = list(manager.chats.keys())[-1]
        manager.current_chat_id = current_session_id

    else:
        # 没有历史记录时，创建第一个会话
        current_session_id = manager.create_chat()

    # 用于后台线程与 UI 通信
    result_queue = queue.Queue()

    # AI 是否正在处理消息
    busy = False

    # 保存“正在思考...”气泡
    thinking_bubble = None
    # 专门保存文件写入确认请求
    approval_queue = queue.Queue()
    # 将界面的确认队列交给文件工具
    set_approval_queue(approval_queue)
    # 创建专门用于 AI 请求的事件循环
    agent_loop = asyncio.new_event_loop()

    # 在后台线程中持续运行事件循环
    def run_agent_loop():
        asyncio.set_event_loop(agent_loop)
        agent_loop.run_forever()

    # 启动事件循环线程
    agent_thread = threading.Thread(
        target=run_agent_loop,
        daemon=True
    )
    agent_thread.start()

    # ========================================
    # 6. 切换聊天
    # ========================================

    def switch_chat(chat_id):
        nonlocal current_session_id

        # AI 正在回复时，暂时不允许切换
        if busy:
            return

        # 更新当前会话 ID
        current_session_id = chat_id
        manager.current_chat_id = chat_id

        # 清空右侧现有气泡
        chat.clear_messages()

        # 读取对应会话的消息
        messages = manager.get_messages(chat_id)

        # 恢复该会话的聊天气泡
        for message in messages:
            chat.add_message(
                message["sender"],
                message["content"]
            )
        refresh_history_highlight()

    # ========================================
    # 7. 创建左侧历史列表
    # ========================================
    def rename_chat(chat_id):
        # AI 正在处理消息时，暂时不允许修改
        if busy:
            return

        # 获取当前聊天标题
        old_title = manager.chats[chat_id]["title"]

        # 创建输入对话框
        dialog = ctk.CTkInputDialog(
            text="请输入新的聊天名称：",
            title="重命名聊天"
        )

        # 等待用户输入
        new_title = dialog.get_input()

        # 用户取消，或者没有输入有效内容
        if new_title is None or not new_title.strip():
            return

        # 更新 ChatManager 中的标题并保存到 JSON
        manager.update_title(chat_id, new_title)

        # 立即更新左侧历史按钮的文字
        history_buttons[chat_id].configure(
            text=manager.chats[chat_id]["title"]
        )

    def confirm_delete(chat_id):
        nonlocal current_session_id

        # AI 正在处理消息时，不允许删除
        if busy:
            messagebox.showinfo(
                "请稍候",
                "请等待 AI 回复完成后再删除聊天。"
            )
            return

        # 检查会话是否存在
        if chat_id not in manager.chats:
            return

        # 获取聊天标题
        chat_title = manager.chats[chat_id]["title"]

        # 弹出确认窗口
        confirmed = messagebox.askyesno(
            "删除聊天",
            f"确定要永久删除「{chat_title}」吗？"
        )

        # 用户取消删除
        if not confirmed:
            return

        # 先删除 SQLite 中的 Agent 记忆
        try:
            asyncio.run(
                delete_agent_session(chat_id)
            )
        except Exception as error:
            messagebox.showerror(
                "删除失败",
                f"无法清除 Agent 记忆：{error}"
            )
            return

        # 再删除 JSON 中的聊天数据
        manager.delete_chat(chat_id)

        # 删除左侧对应的整行控件
        button = history_buttons.pop(chat_id)
        button.master.destroy()

        # 如果删除的是当前聊天
        if current_session_id == chat_id:

            # 清空右侧消息
            chat.clear_messages()

            if manager.chats:
                # 如果还有其他聊天，切换到一个已有会话
                next_chat_id = list(manager.chats.keys())[-1]
                switch_chat(next_chat_id)
            else:
                # 如果全部删除了，创建一个空白新聊天
                current_session_id = manager.create_chat()
                add_history_button(current_session_id)

    history_frame = ctk.CTkScrollableFrame(
        sidebar,
        fg_color="transparent",
        corner_radius=0
    )
    # 隐藏左侧历史列表的滚动条
    history_frame._scrollbar.grid_remove()

    # 注意：
    # 这里只创建容器
    # 后面再创建历史按钮
    # 容器只需要创建一次

    # 用字典保存历史按钮，避免重复创建
    history_buttons = {}

    def add_history_button(chat_id):

        # 防止重复创建历史按钮
        if chat_id in history_buttons:
            return

        # 获取会话标题
        chat_title = manager.chats[chat_id]["title"]

        # 创建一整行容器
        row = ctk.CTkFrame(
            history_frame,
            fg_color="transparent"
        )
        row.pack(fill="x", pady=3)

        # 左边：聊天标题按钮
        button = ctk.CTkButton(
            row,
            text=chat_title,
            anchor="w",
            fg_color="transparent",
            text_color=theme.TEXT_PRIMARY,
            hover_color=theme.BORDER,
            height=38,
            command=lambda cid=chat_id: switch_chat(cid)
        )
        button.pack(
            side="left",
            fill="x",
            expand=True
        )

        # 右边：删除按钮
        delete_button = ctk.CTkButton(
            row,
            text="×",
            width=32,
            height=32,
            fg_color="transparent",
            text_color=theme.TEXT_SECONDARY,
            hover_color=theme.BORDER,
            command=lambda cid=chat_id: confirm_delete(cid)
        )
        delete_button.pack(side="right", padx=(4, 0))
        rename_button = ctk.CTkButton(
            row,
            text="✎",
            width=32,
            height=32,
            fg_color="transparent",
            text_color=theme.TEXT_SECONDARY,
            hover_color=theme.BORDER,
            command=lambda cid=chat_id: rename_chat(cid)
        )

        rename_button.pack(side="right", padx=(4, 0))

        # 保存标题按钮，供自动重命名使用
        history_buttons[chat_id] = button
        # 删除后重新刷新高亮
        refresh_history_highlight()

    # ========================================
    # 8. 新建聊天
    # ========================================

    def new_chat():
        nonlocal current_session_id

        # AI 正在处理消息时，不允许新建
        if busy:
            return

        # 创建一个全新的会话
        current_session_id = manager.create_chat()

        # 清空右侧聊天气泡
        chat.clear_messages()

        # 只添加刚创建的这一个历史按钮
        add_history_button(current_session_id)
        refresh_history_highlight()

    # ========================================
    # 9. 创建新建聊天按钮
    # ========================================

    new_chat_button = ctk.CTkButton(
        sidebar,
        text="+ 新建聊天",
        fg_color=theme.PRIMARY_BLUE,
        hover_color=theme.PRIMARY_HOVER,
        corner_radius=theme.CORNER_RADIUS,
        height=42,
        command=new_chat
    )

    new_chat_button.pack(
        padx=16,
        fill="x"
    )

    # 将历史列表放在新建按钮下面
    history_frame.pack(
        fill="both",
        expand=True,
        padx=12,
        pady=(20, 10)
    )

    # ========================================
    # 10. 启动时恢复历史聊天
    # ========================================

    # 这里位于 start_ui() 内部
    # 但不在 new_chat() 内部
    # 因此只会在启动时执行一次
    def refresh_history_highlight():
        # 遍历所有历史聊天按钮
        for chat_id, button in history_buttons.items():

            # 判断是不是当前聊天
            if chat_id == current_session_id:
                button.configure(
                    fg_color="#DBEAFE",
                    text_color=theme.PRIMARY_BLUE
                )
            else:
                button.configure(
                    fg_color="transparent",
                    text_color=theme.TEXT_PRIMARY
                )
    for chat_id in manager.chats:
        add_history_button(chat_id)

    # 恢复当前会话的消息
    for message in manager.get_messages(current_session_id):
        chat.add_message(
            message["sender"],
            message["content"]
        )
    # 程序启动后，高亮当前聊天
    refresh_history_highlight()


    # ========================================
    # 11. 处理用户发送消息
    # ========================================

    def handle_send(message):
        nonlocal busy, thinking_bubble

        if busy:
            return

        # 标记 AI 开始处理消息
        busy = True

        # 禁用发送按钮
        input_area.set_busy(True)

        # 显示用户消息
        chat.add_message("user", message)

        # 保存用户消息到 ChatManager
        manager.add_message(
            current_session_id,
            "user",
            message
        )
        # 如果这是当前会话的第一条消息
        messages = manager.get_messages(current_session_id)

        if len(messages) == 1:
            # 使用第一条消息作为标题
            manager.update_title(current_session_id, message)

            # 同步修改左侧按钮的文字
            history_buttons[current_session_id].configure(
                text=manager.chats[current_session_id]["title"]
            )

        # 显示“正在思考...”气泡
        thinking_bubble = chat.add_message(
            "ai",
            "正在思考..."
        )

        # 保存本次请求的会话 ID
        request_session_id = current_session_id

        def worker():
            try:
                # 将 AI 请求提交到长期运行的事件循环
                future = asyncio.run_coroutine_threadsafe(
                    ask_agent(message, request_session_id),
                    agent_loop
                )

                # 等待 AI 返回结果
                reply = future.result()
                print("[GUI收到的回复]", repr(reply))

            except Exception as error:
                # 打印完整错误信息，方便排查
                traceback.print_exc()

                # 将错误显示在聊天界面
                reply = f"发生错误：{error}"

            # 将结果交给主界面线程
            result_queue.put((request_session_id, reply))

        # 启动后台线程
        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    # ========================================
    # 12. 检查 AI 回复
    # ========================================

    def check_results():
        """在 Tk 主线程保存回复并重建聊天气泡，避免旧气泡高度失效。"""
        nonlocal busy, thinking_bubble

        try:
            while True:
                request_session_id, reply = result_queue.get_nowait()

                try:
                    # 先保存结果：即使后续渲染失败，聊天记录也不会丢失。
                    manager.add_message(request_session_id, "ai", reply)

                    # 只有当前会话才需要更新右侧界面。
                    if request_session_id == current_session_id:
                        # 删除临时“正在思考...”气泡和旧布局，
                        # 从保存的聊天记录重新构建正式气泡。
                        chat.clear_messages()
                        thinking_bubble = None

                        for message in manager.get_messages(request_session_id):
                            chat.add_message(
                                message["sender"],
                                message["content"],
                            )

                except Exception:
                    traceback.print_exc()
                    # 显示失败时不让输入框永久锁死。
                    # 回复已保存，可切换会话重新加载。
                finally:
                    busy = False
                    input_area.set_busy(False)

        except queue.Empty:
            pass
        finally:
            window.after(100, check_results)

    def check_approvals():
        """
        检查 Agent 发来的文件操作确认请求。

        支持：
        write   创建文件
        append  追加内容
        restore 恢复历史快照
        """

        try:
            # 尝试获取一个确认请求
            request = approval_queue.get_nowait()

        except queue.Empty:
            # 当前没有确认请求
            pass

        else:
            # 默认拒绝，确保出现异常时不会误批准
            approved = False

            try:
                filename = request["filename"]
                content = request.get("content", "")
                operation = request.get("operation", "write")

                # 根据操作类型选择说明
                if operation == "write":
                    action_text = "创建新文件"

                elif operation == "append":
                    action_text = "向已有文件追加内容"

                elif operation == "restore":
                    action_text = "从历史快照恢复文件"

                else:
                    action_text = None

                # 不认识的操作，不弹确认框，直接拒绝
                if action_text is not None:

                    # 恢复操作需要特别提示
                    if operation == "restore":
                        backup_name = request.get(
                            "backup_name",
                            "未知备份"
                        )

                        message = (
                            f"AI 请求：{action_text}\n\n"
                            f"原文件：{filename}\n"
                            f"恢复来源：{backup_name}\n\n"
                            "注意：恢复会替换当前文件内容。\n"
                            "程序将在恢复前备份当前版本。\n\n"
                            "是否允许恢复？"
                        )

                    else:
                        # 创建和追加操作显示内容预览
                        preview = content[:300]

                        if len(content) > 300:
                            preview += "\n……（内容过长，已省略）"

                        message = (
                            f"AI 请求：{action_text}\n\n"
                            f"文件名：{filename}\n\n"
                            f"准备写入的内容：\n{preview}\n\n"
                            "是否允许？"
                        )

                    # 弹出系统确认窗口
                    approved = messagebox.askyesno(
                        "文件操作确认",
                        message
                    )

            except Exception as error:
                # 打印错误，方便在 PyCharm 控制台排查
                print(f"[确认窗口错误] {error}")

            finally:
                # 不管成功、拒绝还是发生异常，
                # 都通知等待中的 Agent
                request["approved"] = approved
                request["event"].set()

        # 每隔 100 毫秒检查一次
        window.after(100, check_approvals)

    # ========================================
    # 13. 创建底部输入区域
    # ========================================

    input_area = InputArea(
        chat_area,
        on_send=handle_send
    )
    input_area.pack(fill="x")

    def on_closing():
        # 如果 AI 正在回复，暂时不允许关闭
        if busy:
            messagebox.showinfo(
                "请稍候",
                "AI 正在回复，请等待完成后再关闭。"
            )
            return

        # 防止用户重复点击关闭按钮
        window.protocol("WM_DELETE_WINDOW", lambda: None)

        # 在后台事件循环中关闭网络客户端
        async def cleanup():
            await close_ai_client()

        future = asyncio.run_coroutine_threadsafe(
            cleanup(),
            agent_loop
        )

        # 等待网络连接关闭
        # 注意：这一步暂时在主线程等待，
        # 正常情况下时间很短
        try:
            future.result(timeout=5)
        except Exception as error:
            print("关闭网络客户端时出现问题：", error)

        # 通知后台事件循环停止
        agent_loop.call_soon_threadsafe(agent_loop.stop)

        # 等待后台线程结束
        agent_thread.join(timeout=5)

        # 事件循环停止后，关闭事件循环
        if not agent_thread.is_alive():
            agent_loop.close()
        else:
            print("后台线程尚未退出，跳过关闭事件循环")

        # 最后关闭窗口
        window.destroy()

    check_results()

    # 开始监听文件写入确认请求
    check_approvals()

    window.protocol("WM_DELETE_WINDOW", on_closing)

    window.mainloop()

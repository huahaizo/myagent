"""聊天消息区域：Markdown、文本选择、可靠的会话切换与清空。"""

import tkinter as tk
import customtkinter as ctk

from ui import theme
from ui.markdown_renderer import render_markdown


class ChatArea(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BACKGROUND, corner_radius=0)
        self._scrollbar.grid_remove()
        self.grid_columnconfigure(0, weight=1)
        self._message_rows = []
        self._message_count = 0
        self._generation = 0
        self._scroll_job = None

    def clear_messages(self):
        """只删除本类创建的消息行，不触碰滚动容器内部控件。"""
        self._generation += 1
        if self._scroll_job is not None:
            try:
                self.after_cancel(self._scroll_job)
            except (tk.TclError, ValueError):
                pass
            self._scroll_job = None

        for row in self._message_rows:
            if row.winfo_exists():
                row.destroy()
        self._message_rows.clear()
        self._message_count = 0

        # 旧消息清空后恢复到顶部；新消息加入时再滚到底部。
        self.after_idle(self._scroll_to_top)

    def _scroll_to_top(self):
        if self.winfo_exists():
            self._parent_canvas.yview_moveto(0.0)

    def _schedule_scroll_bottom(self, generation):
        if self._scroll_job is not None:
            try:
                self.after_cancel(self._scroll_job)
            except (tk.TclError, ValueError):
                pass
        self._scroll_job = self.after(
            80, lambda: self._scroll_bottom_if_current(generation)
        )

    def _scroll_bottom_if_current(self, generation):
        self._scroll_job = None
        if not self.winfo_exists() or generation != self._generation:
            return
        self._parent_canvas.yview_moveto(1.0)

    def resize_markdown_bubble(self, bubble: tk.Text):
        """根据渲染后的显示行数调整高度，避免空白或文本被截断。"""
        if not bubble.winfo_exists():
            return
        try:
            bubble.update_idletasks()
            result = bubble.count('1.0', 'end-1c', 'displaylines')
            lines = result[0] if result else 1
            bubble.configure(height=max(2, lines + 2))
        except tk.TclError:
            return
        self._schedule_scroll_bottom(self._generation)

    def add_message(self, sender: str, message: str):
        """添加一条消息，返回 tk.Text 以兼容现有 chat_window.py。"""
        is_user = sender == 'user'
        bubble_color = theme.USER_BUBBLE if is_user else theme.AI_BUBBLE
        text_color = '#FFFFFF' if is_user else theme.TEXT_PRIMARY

        message_row = ctk.CTkFrame(
            self, fg_color='transparent', corner_radius=0
        )
        message_row.grid(
            row=self._message_count,
            column=0,
            sticky='ew',
            padx=20,
            pady=8,
        )
        self._message_rows.append(message_row)
        self._message_count += 1

        container = ctk.CTkFrame(
            message_row,
            fg_color=bubble_color,
            corner_radius=20,
            border_width=0,
        )
        container.pack(
            side='right' if is_user else 'left',
            padx=10,
            pady=5,
        )

        bubble = tk.Text(
            container,
            width=40 if is_user else 55,
            height=2,
            wrap='word',
            bg=bubble_color,
            fg=text_color,
            selectbackground='#93C5FD' if is_user else '#BFDBFE',
            selectforeground='#111827',
            font=(theme.FONT_FAMILY, theme.FONT_SIZE),
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            padx=10,
            pady=6,
            cursor='xterm',
            insertwidth=0,
            takefocus=True,
        )
        bubble.pack(padx=10, pady=(12, 12))
        bubble.original_message = message

        render_markdown(bubble, message)
        generation = self._generation
        self.after_idle(
            lambda b=bubble, g=generation: (
                self.resize_markdown_bubble(b)
                if self.winfo_exists() and g == self._generation and b.winfo_exists()
                else None
            )
        )
        return bubble

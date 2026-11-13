
import customtkinter as ctk

# 导入我们自己定义的颜色、字体等主题配置
from ui import theme


# 创建输入区域组件
# 继承 CTkFrame，说明 InputArea 本身也是一个框架
class InputArea(ctk.CTkFrame):

    def __init__(self, master, on_send):

        # 初始化父类
        super().__init__(
            master,
            fg_color=theme.BACKGROUND,
            corner_radius=0
        )

        # 保存外部传入的消息发送函数
        # 注意：这里保存的是函数本身，并没有执行
        self.on_send = on_send

        # 记录 AI 是否正在处理消息
        # False = 可以发送
        # True = 暂时不能发送
        self.busy = False

        # ==================================
        # 1. 创建输入框外层容器
        # ==================================

        input_frame = ctk.CTkFrame(
            self,
            fg_color="#FFFFFF",
            border_width=1,
            border_color=theme.BORDER,
            corner_radius=16
        )

        input_frame.pack(
            fill="x",          # 水平方向填满
            padx=24,           # 左右外边距
            pady=(8, 20)       # 上边距8，下边距20
        )

        # ==================================
        # 2. 创建多行文本输入框
        # ==================================

        self.textbox = ctk.CTkTextbox(
            input_frame,
            height=75,
            fg_color="transparent",
            border_width=0,
            font=(
                theme.FONT_FAMILY,
                theme.FONT_SIZE
            ),
            wrap="word"        # 按单词自动换行
        )

        self.textbox.pack(
            fill="x",
            padx=12,
            pady=(10, 0)
        )

        # ==================================
        # 3. 创建底部操作栏
        # ==================================

        bottom_bar = ctk.CTkFrame(
            input_frame,
            fg_color="transparent"
        )

        bottom_bar.pack(
            fill="x",
            padx=12,
            pady=(0, 10)
        )

        # 显示快捷键提示
        hint = ctk.CTkLabel(
            bottom_bar,
            text="Enter 发送 · Shift + Enter 换行",
            text_color=theme.TEXT_SECONDARY,
            font=(theme.FONT_FAMILY, 11)
        )

        hint.pack(side="left")

        # ==================================
        # 4. 创建发送按钮
        # ==================================

        # 使用 self.send_button
        # 这样其他方法也能访问并修改按钮状态
        self.send_button = ctk.CTkButton(
            bottom_bar,
            text="↑",
            width=36,
            height=36,
            corner_radius=10,
            fg_color=theme.PRIMARY_BLUE,
            hover_color=theme.PRIMARY_HOVER,

            # 点击按钮时调用发送方法
            command=self.send_message
        )

        self.send_button.pack(side="right")

        # ==================================
        # 5. 绑定 Enter 键
        # ==================================

        # 当用户按下 Enter 时
        # 自动执行 handle_enter 方法
        self.textbox.bind(
            "<Return>",
            self.handle_enter
        )

    # ==================================
    # 6. 处理 Enter / Shift + Enter
    # ==================================

    def handle_enter(self, event):

        # 检查 Shift 是否被按住
        # 如果按住 Shift，就允许输入框正常换行
        if event.state & 0x0001:
            return

        # 普通 Enter：发送消息
        self.send_message()

        # 阻止 Enter 自动插入换行符
        return "break"

    # ==================================
    # 7. 发送用户消息
    # ==================================

    def send_message(self):

        # 如果 AI 正在处理消息
        # 就不允许再次发送
        if self.busy:
            return

        # 获取输入框中的全部文本
        # 1.0 表示第一行第0个字符
        # end-1c 表示最后一个实际字符
        # strip() 去除首尾空白
        message = self.textbox.get(
            "1.0",
            "end-1c"
        ).strip()

        # 不发送空消息
        if not message:
            return

        # 调用外部传入的发送函数
        # 由 chat_window.py 负责处理消息
        self.on_send(message)

        # 发送后清空输入框
        self.textbox.delete("1.0", "end")

    # ==================================
    # 8. 控制 AI 忙碌状态
    # ==================================

    def set_busy(self, busy: bool):

        # 保存当前状态
        self.busy = busy

        if busy:
            # AI 正在思考：
            # 禁用发送按钮，并把按钮变灰
            self.send_button.configure(
                state="disabled",
                fg_color="#9CA3AF"
            )

        else:
            # AI 已经回复：
            # 恢复按钮，并变回蓝色
            self.send_button.configure(
                state="normal",
                fg_color=theme.PRIMARY_BLUE
            )

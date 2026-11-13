"""将 Markdown 渲染到 tkinter.Text；不执行 Markdown 中的 HTML。"""
import tkinter as tk
from markdown_it import MarkdownIt
from ui import theme

_md = MarkdownIt('commonmark', {'html': False})


def render_markdown(widget: tk.Text, content: str) -> None:
    widget.configure(state='normal')
    widget.delete('1.0', 'end')
    family = theme.FONT_FAMILY
    size = theme.FONT_SIZE
    widget.tag_configure('h1', font=(family, size + 7, 'bold'), spacing1=8, spacing3=5)
    widget.tag_configure('h2', font=(family, size + 5, 'bold'), spacing1=6, spacing3=4)
    widget.tag_configure('h3', font=(family, size + 3, 'bold'), spacing1=4, spacing3=3)
    widget.tag_configure('bold', font=(family, size, 'bold'))
    widget.tag_configure('italic', font=(family, size, 'italic'))
    # 用户蓝色气泡上的代码使用浅蓝背景和深色文字，保证可读性。
    is_user = str(widget.cget('bg')).lower() == str(theme.USER_BUBBLE).lower()
    code_bg = '#DBEAFE' if is_user else '#E8EDF3'
    code_fg = '#172554' if is_user else theme.TEXT_PRIMARY
    quote_fg = '#DBEAFE' if is_user else '#64748B'
    widget.tag_configure('code', font=('Consolas', size), background=code_bg, foreground=code_fg)
    widget.tag_configure('codeblock', font=('Consolas', size), background=code_bg, foreground=code_fg, spacing1=5, spacing3=5)
    widget.tag_configure('quote', foreground=quote_fg, lmargin1=12, lmargin2=12)

    heading = None
    bold = False
    italic = False
    quote_depth = 0
    list_stack = []
    item_counter = []
    tokens = _md.parse(content)

    def add(value: str, extra=()):
        tags = list(extra)
        if heading in ('h1', 'h2', 'h3'):
            tags.append(heading)
        if bold:
            tags.append('bold')
        if italic:
            tags.append('italic')
        if quote_depth:
            tags.append('quote')
        widget.insert('end', value, tuple(tags))

    for token in tokens:
        kind = token.type
        if kind == 'heading_open':
            heading = token.tag
        elif kind == 'heading_close':
            heading = None
            add('\n')
        elif kind == 'blockquote_open':
            quote_depth += 1
        elif kind == 'blockquote_close':
            quote_depth = max(0, quote_depth - 1)
        elif kind in ('bullet_list_open', 'ordered_list_open'):
            list_stack.append(kind)
            item_counter.append(int(token.attrGet('start') or 1))
        elif kind in ('bullet_list_close', 'ordered_list_close'):
            list_stack.pop()
            item_counter.pop()
            if not list_stack:
                add('\n')
        elif kind == 'list_item_open':
            if list_stack:
                indent = '  ' * (len(list_stack) - 1)
                if list_stack[-1] == 'ordered_list_open':
                    prefix = f'{item_counter[-1]}. '
                    item_counter[-1] += 1
                else:
                    prefix = '• '
                add(indent + prefix)
        elif kind == 'list_item_close':
            add('\n')
        elif kind == 'paragraph_close':
            # 列表项的换行由 list_item_close 负责
            if not list_stack:
                add('\n\n')
        elif kind in ('fence', 'code_block'):
            add(token.content.rstrip('\n') + '\n\n', ('codeblock',))
        elif kind == 'hr':
            add('────────────\n')
        elif kind == 'inline':
            for child in token.children or []:
                t = child.type
                if t == 'strong_open':
                    bold = True
                elif t == 'strong_close':
                    bold = False
                elif t == 'em_open':
                    italic = True
                elif t == 'em_close':
                    italic = False
                elif t == 'text':
                    add(child.content)
                elif t == 'code_inline':
                    add(child.content, ('code',))
                elif t in ('softbreak', 'hardbreak'):
                    add('\n')
                elif t == 'image':
                    add(child.content or '[图片]')
                # 链接的可见文本由其内部 text token 显示，不打开网页

    widget.configure(state='disabled')

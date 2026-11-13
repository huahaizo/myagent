
import asyncio
import threading
from pathlib import Path
import shutil
from datetime import datetime
from agents import function_tool


# 获取项目根目录
PROJECT_DIR = Path(__file__).resolve().parent.parent

# AI 允许访问的文件夹
WORKSPACE_DIR = PROJECT_DIR / "workspace"
# 存放文件快照的目录
BACKUP_DIR = WORKSPACE_DIR / "backups"
# 保存主界面传来的确认队列
approval_queue = None


def set_approval_queue(q):
    global approval_queue
    approval_queue = q

def backup_txt_file(file_path: Path) -> Path:
    """
    给 workspace 中的 TXT 文件创建一份备份。

    参数：
        file_path：需要备份的文件路径

    返回：
        backup_path：创建成功的备份文件路径
    """

    # 1. 确保文件在 workspace 中
    file_path = file_path.resolve()

    if not file_path.is_relative_to(WORKSPACE_DIR.resolve()):
        raise ValueError("不允许备份 workspace 以外的文件")

    # 2. 确保是 TXT 文件
    if file_path.suffix.lower() != ".txt":
        raise ValueError("只能备份 TXT 文件")

    # 3. 确保原文件存在
    if not file_path.is_file():
        raise FileNotFoundError("需要备份的文件不存在")

    # 4. 创建 backups 文件夹
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # 5. 生成时间戳
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # 6. 生成备份文件名
    backup_name = f"{file_path.stem}_{timestamp}.txt"

    # 7. 拼接备份文件路径
    backup_path = BACKUP_DIR / backup_name

    # 8. 复制文件
    shutil.copy2(file_path, backup_path)

    # 9. 返回备份路径
    return backup_path


@function_tool
def read_txt_file(filename: str) -> str:
    """
    读取 workspace 中的 TXT 文件。
    """

    file_path = (WORKSPACE_DIR / filename).resolve()

    # 限制访问范围
    if not file_path.is_relative_to(WORKSPACE_DIR.resolve()):
        return "错误：不允许读取 workspace 以外的文件。"

    # 限制文件类型
    if file_path.suffix.lower() != ".txt":
        return "错误：只允许读取 TXT 文件。"

    # 检查文件是否存在
    if not file_path.is_file():
        return "错误：文件不存在。"

    # 限制文件大小
    if file_path.stat().st_size > 100_000:
        return "错误：文件太大。"

    try:
        return file_path.read_text(encoding="utf-8")

    except (OSError, UnicodeError) as error:
        return f"读取文件失败：{error}"


@function_tool
def list_workspace_files() -> str:
    """
    列出 workspace 中的 TXT 文件。
    """

    if not WORKSPACE_DIR.is_dir():
        return "错误：workspace 文件夹不存在。"

    files = []

    for file in WORKSPACE_DIR.iterdir():
        if (
            file.is_file()
            and not file.is_symlink()
            and file.suffix.lower() == ".txt"
        ):
            files.append(file.name)

    if not files:
        return "workspace 中没有 TXT 文件。"

    files.sort()

    return "workspace 中的 TXT 文件：\n" + "\n".join(files)


def wait_for_approval(request):
    """
    在普通工作线程中等待用户确认。
    避免阻塞 Agent 的异步事件循环。
    """

    return request["event"].wait(timeout=60)


@function_tool
async def write_txt_file(filename: str, content: str) -> str:
    """
    创建新的 TXT 文件。
    必须经过用户确认，不允许覆盖已有文件。
    """

    # 1. 检查文件路径
    file_path = (WORKSPACE_DIR / filename).resolve()

    if not file_path.is_relative_to(WORKSPACE_DIR.resolve()):
        return "错误：不允许写入 workspace 以外的文件。"

    # 2. 只允许 TXT 文件
    if file_path.suffix.lower() != ".txt":
        return "错误：只允许创建 TXT 文件。"

    # 3. 不允许覆盖
    if file_path.exists():
        return "错误：文件已经存在，不允许覆盖。"

    # 4. 限制内容大小
    if len(content.encode("utf-8")) > 100_000:
        return "错误：文件内容太大。"

    # 5. 没有确认队列时，拒绝写入
    if approval_queue is None:
        return "错误：没有配置文件写入确认功能。"

    # 6. 创建确认请求
    approval_event = threading.Event()

    request = {
        "filename": filename,
        "content": content,
        "approved": False,
        "operation": "write",  # 表示创建新文件
        "event": approval_event,
    }

    # 7. 通知主界面弹出确认窗口
    approval_queue.put(request)

    # 8. 在工作线程中等待，避免阻塞事件循环
    confirmed_in_time = await asyncio.to_thread(
        wait_for_approval,
        request
    )

    # 9. 超时则拒绝写入
    if not confirmed_in_time:
        return "文件写入已取消：等待确认超时。"

    # 10. 用户拒绝则不写入
    if not request["approved"]:
        return "用户拒绝了文件写入操作。"

    # 11. 用户批准后才创建文件
    try:
        # 再次检查路径，避免确认期间文件状态发生变化
        file_path = (WORKSPACE_DIR / filename).resolve()

        if not file_path.is_relative_to(WORKSPACE_DIR.resolve()):
            return "错误：文件路径不安全。"

        # x 模式保证不会覆盖已有文件
        with file_path.open("x", encoding="utf-8") as file:
            file.write(content)

        return f"文件创建成功：{filename}"

    except FileExistsError:
        return "错误：文件已经存在，不允许覆盖。"

    except OSError as error:
        return f"写入文件失败：{error}"

@function_tool
async def append_txt_file(filename: str, content: str) -> str:
    """
    向 workspace 中已有的 TXT 文件末尾追加内容。
    必须经过用户确认。
    """

    # 1. 检查文件路径
    file_path = (WORKSPACE_DIR / filename).resolve()

    if not file_path.is_relative_to(WORKSPACE_DIR.resolve()):
        return "错误：不允许修改 workspace 以外的文件。"

    # 2. 只允许 TXT 文件
    if file_path.suffix.lower() != ".txt":
        return "错误：只允许修改 TXT 文件。"

    # 3. 必须是已经存在的普通文件
    if not file_path.is_file():
        return "错误：文件不存在，无法追加。"

    # 4. 限制追加内容大小
    if len(content.encode("utf-8")) > 100_000:
        return "错误：追加内容太大。"

    # 5. 没有确认队列时禁止修改
    if approval_queue is None:
        return "错误：没有配置用户确认功能。"

    # 6. 创建确认请求
    approval_event = threading.Event()

    request = {
        "filename": filename,
        "content": content,
        "operation": "append",
        "approved": False,
        "event": approval_event,
    }

    # 7. 发送到主界面
    approval_queue.put(request)

    # 8. 异步等待用户确认
    confirmed_in_time = await asyncio.to_thread(
        wait_for_approval,
        request
    )

    if not confirmed_in_time:
        return "追加已取消：等待确认超时。"

    if not request["approved"]:
        return "用户拒绝了追加操作。"

    # 9. 确认后再次检查文件
    file_path = (WORKSPACE_DIR / filename).resolve()

    if not file_path.is_relative_to(WORKSPACE_DIR.resolve()):
        return "错误：文件路径不安全。"

    if not file_path.is_file():
        return "错误：文件已经不存在。"

    # 10. 追加内容

    # 10. 先备份，再追加内容
    try:
        # 第一步：创建原文件的快照
        backup_path = backup_txt_file(file_path)

        # 第二步：备份成功后，才允许修改原文件
        with file_path.open("a", encoding="utf-8") as file:
            file.write("\n" + content)

        # 第三步：告诉用户操作结果
        return (
            f"内容已追加到：{filename}\n"
            f"修改前的备份已保存：{backup_path.name}"
        )

    except (OSError, ValueError) as error:
        return f"备份或追加失败：{error}"


@function_tool
def list_file_backups(filename: str) -> str:
    """
    查看指定 TXT 文件的历史备份。

    Args:
        filename: 原文件名，例如 学习笔记.txt
    """

    # 1. 只允许查询 workspace 根目录中的 TXT 文件
    # 禁止传入 ../ 或其他目录路径
    if Path(filename).name != filename:
        return "错误：只能查询 workspace 根目录中的文件。"

    if Path(filename).suffix.lower() != ".txt":
        return "错误：只支持 TXT 文件。"

    # 2. 检查备份目录
    if not BACKUP_DIR.is_dir():
        return "目前还没有备份记录。"

    # 3. 根据原文件名生成匹配前缀
    # 例如：学习笔记_
    prefix = Path(filename).stem + "_"

    # 4. 收集匹配的备份文件
    backups = []

    for file in BACKUP_DIR.iterdir():
        if (
            file.is_file()
            and not file.is_symlink()
            and file.suffix.lower() == ".txt"
            and file.name.startswith(prefix)
        ):
            backups.append(file.name)

    # 5. 没有找到备份
    if not backups:
        return f"没有找到 {filename} 的历史备份。"

    # 6. 按文件名倒序排列
    # 时间戳越新，通常排得越靠前
    backups.sort(reverse=True)

    # 7. 返回备份列表
    return (
        f"{filename} 的历史备份（最新在前）：\n"
        + "\n".join(backups)
    )

@function_tool
async def restore_txt_backup(filename: str, backup_name: str) -> str:
    """
    从历史备份恢复 TXT 文件。

    恢复流程：
    1. 检查原文件和备份文件
    2. 请求用户确认
    3. 备份当前文件
    4. 恢复历史内容
    """

    import os
    import tempfile

    # 1. 只允许 workspace 根目录中的 TXT 文件
    if Path(filename).name != filename:
        return "错误：原文件名不合法。"

    if Path(filename).suffix.lower() != ".txt":
        return "错误：只能恢复 TXT 文件。"

    # 2. 备份名称也只能是单独的文件名
    if Path(backup_name).name != backup_name:
        return "错误：备份文件名不合法。"

    if Path(backup_name).suffix.lower() != ".txt":
        return "错误：备份文件必须是 TXT 文件。"

    # 3. 检查备份文件是否属于指定原文件
    prefix = Path(filename).stem + "_"

    if not backup_name.startswith(prefix):
        return "错误：备份文件与原文件不匹配。"

    # 4. 构造文件路径
    file_path = WORKSPACE_DIR / filename
    backup_path = BACKUP_DIR / backup_name

    # 拒绝符号链接，避免通过链接操作其他文件
    if file_path.is_symlink() or backup_path.is_symlink():
        return "错误：不允许操作符号链接。"

    # 5. 确保文件存在
    if not file_path.is_file():
        return "错误：原文件不存在。"

    if not backup_path.is_file():
        return "错误：找不到指定的历史备份。"

    # 6. 检查路径范围
    if not file_path.resolve().is_relative_to(WORKSPACE_DIR.resolve()):
        return "错误：原文件路径不安全。"

    if not backup_path.resolve().is_relative_to(BACKUP_DIR.resolve()):
        return "错误：备份文件路径不安全。"

    # 7. 检查确认队列
    if approval_queue is None:
        return "错误：没有配置用户确认功能。"

    # 8. 创建确认请求
    approval_event = threading.Event()

    request = {
        "filename": filename,
        "backup_name": backup_name,
        "content": f"准备从历史备份恢复：{backup_name}",
        "operation": "restore",
        "approved": False,
        "event": approval_event,
    }

    approval_queue.put(request)

    # 9. 等待用户确认
    confirmed_in_time = await asyncio.to_thread(
        wait_for_approval,
        request
    )

    if not confirmed_in_time:
        return "恢复已取消：等待确认超时。"

    if not request["approved"]:
        return "用户拒绝了文件恢复操作。"

    # 10. 用户确认后，再次检查文件状态
    if file_path.is_symlink() or backup_path.is_symlink():
        return "错误：文件路径发生变化，恢复已取消。"

    if not file_path.is_file() or not backup_path.is_file():
        return "错误：文件不存在，恢复已取消。"

    if not file_path.resolve().is_relative_to(WORKSPACE_DIR.resolve()):
        return "错误：原文件路径不安全。"

    if not backup_path.resolve().is_relative_to(BACKUP_DIR.resolve()):
        return "错误：备份路径不安全。"

    temp_path = None

    try:
        # 11. 先保存当前文件的快照
        current_backup = backup_txt_file(file_path)

        # 12. 在原文件所在目录创建临时文件
        # 使用同一目录，方便之后进行替换
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=WORKSPACE_DIR,
            prefix=".restore_",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            # 把历史备份复制到临时文件
            with backup_path.open("rb") as source:
                shutil.copyfileobj(source, temp_file)

        # 13. 用临时文件替换原文件
        os.replace(temp_path, file_path)
        temp_path = None

        return (
            f"文件恢复成功：{filename}\n"
            f"恢复来源：{backup_name}\n"
            f"恢复前的版本已备份：{current_backup.name}"
        )

    except (OSError, ValueError) as error:
        return f"文件恢复失败：{error}"

    finally:
        # 如果恢复失败，清理尚未替换的临时文件
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

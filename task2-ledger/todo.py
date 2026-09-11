"""命令行待办事项应用（单文件，无第三方依赖）。

用法:
    python todo.py add 买牛奶      # 添加一条待办事项
    python todo.py list           # 显示所有待办事项
    python todo.py done 1         # 把第 1 条标记为已完成
    python todo.py delete 1       # 删除第 1 条

数据保存在脚本同目录下的 todos.json，重启后依然有效。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "todos.json"

USAGE = """用法: python todo.py <命令> [参数]

命令:
  add <内容>     添加一条待办事项
  list           显示所有待办事项
  done <编号>    把指定编号的事项标记为已完成
  delete <编号>  删除指定编号的事项
"""


def load_todos() -> list[dict]:
    """读取 todos.json；文件不存在视为空列表。"""
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, OSError) as exc:
        # 不静默清空，先让用户处理坏文件，避免覆盖丢数据
        print(f"错误：无法读取数据文件 {DATA_FILE}（{exc}）。")
        print("本次操作已取消，请检查该文件后重试。")
        sys.exit(1)
    if not isinstance(data, list):
        print(f"错误：{DATA_FILE} 内容格式不正确，应为待办事项列表。")
        sys.exit(1)
    return data


def save_todos(todos: list[dict]) -> None:
    try:
        DATA_FILE.write_text(
            json.dumps(todos, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"错误：写入数据文件失败（{exc}）。")
        sys.exit(1)


def parse_index(raw: str, todos: list[dict]) -> int | None:
    """把用户输入的编号转换为列表下标；无效时打印提示并返回 None。"""
    if not raw.isdigit():
        print(f"错误：编号应为正整数，收到的是“{raw}”。")
        return None
    number = int(raw)
    if not 1 <= number <= len(todos):
        print(f"错误：编号 {number} 不存在，当前共有 {len(todos)} 条待办事项。")
        return None
    return number - 1


def show_item(number: int, item: dict) -> None:
    mark = "x" if item["done"] else " "
    print(f"{number}. [{mark}] {item['text']}")


def cmd_add(args: list[str], todos: list[dict]) -> None:
    if not args:
        print("错误：add 命令需要待办内容，例如：python todo.py add 买牛奶")
        return
    todos.append({"text": " ".join(args), "done": False})
    save_todos(todos)
    show_item(len(todos), todos[-1])


def cmd_list(_args: list[str], todos: list[dict]) -> None:
    if not todos:
        print("暂无待办事项，用 add 命令添加一条吧。")
        return
    for number, item in enumerate(todos, start=1):
        show_item(number, item)


def cmd_done(args: list[str], todos: list[dict]) -> None:
    if len(args) != 1:
        print("错误：done 命令需要一个编号，例如：python todo.py done 1")
        return
    index = parse_index(args[0], todos)
    if index is None:
        return
    todos[index]["done"] = True
    save_todos(todos)
    show_item(index + 1, todos[index])


def cmd_delete(args: list[str], todos: list[dict]) -> None:
    if len(args) != 1:
        print("错误：delete 命令需要一个编号，例如：python todo.py delete 1")
        return
    index = parse_index(args[0], todos)
    if index is None:
        return
    removed = todos.pop(index)
    save_todos(todos)
    print(f"已删除：{removed['text']}")


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "done": cmd_done,
    "delete": cmd_delete,
}


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, end="")
        return 0
    command, args = argv[0], argv[1:]
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"未知命令：{command}")
        print(USAGE, end="")
        return 2
    handler(args, load_todos())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

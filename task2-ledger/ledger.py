"""命令行记账本——最小闭环（记一笔 + 退出）。

运行:  python ledger.py
数据:  保存在脚本同目录下的 data.json，重启后自动加载。
后续:  流水查看、汇总统计暂未实现。
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parent / "data.json"
DEFAULT_CATEGORY = "未分类"


def load_records() -> list[dict]:
    """启动时读取 data.json；文件不存在或损坏时从空账本开始。"""
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (json.JSONDecodeError, OSError) as exc:
        print(f"警告：{DATA_FILE} 读取失败（{exc}），本次从空账本开始。")
        return []
    if not isinstance(data, list):
        print(f"警告：{DATA_FILE} 内容格式不正确，本次从空账本开始。")
        return []
    return data


def save_records(records: list[dict]) -> None:
    DATA_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def input_amount() -> float:
    """循环询问，直到拿到合法的正数金额（支持小数）。"""
    while True:
        raw = input("金额（元，支持小数）: ").strip()
        try:
            amount = float(raw)
        except ValueError:
            print("  金额没看懂，请输入数字，例如 25.5")
            continue
        if not math.isfinite(amount):
            print("  金额不能是 inf/nan，请重新输入。")
            continue
        if amount <= 0:
            print("  金额应大于 0，请重新输入。")
            continue
        return round(amount, 2)


def input_category() -> str:
    raw = input(f"分类（直接回车默认「{DEFAULT_CATEGORY}」）: ").strip()
    return raw or DEFAULT_CATEGORY


def input_note() -> str:
    return input("备注（可留空）: ").strip()


def add_record(records: list[dict]) -> None:
    print("--- 记一笔 ---")
    amount = input_amount()
    category = input_category()
    note = input_note()
    records.append(
        {
            "amount": amount,
            "category": category,
            "note": note,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    )
    save_records(records)
    summary = f"已记下：{amount} 元 [{category}]"
    if note:
        summary += f" {note}"
    print(summary + f"（当前共 {len(records)} 笔）")


def main() -> None:
    records = load_records()
    print(f"账本已加载，当前共 {len(records)} 笔。")
    while True:
        print()
        print("==== 记账本 ====")
        print("1 记一笔")
        print("2 退出")
        choice = input("请选择: ").strip()
        if choice == "1":
            add_record(records)
        elif choice == "2":
            print("再见！数据已保存在 data.json。")
            break
        else:
            print(f"没有这个选项：{choice}，请输入 1 或 2。")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n已退出，数据已保存在 data.json。")

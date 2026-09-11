"""命令行记账本——最小闭环（记一笔 + 退出）。

运行:  python ledger.py
数据:  保存在脚本同目录下的 data.json，重启后自动加载。
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


def show_records(records: list[dict]) -> None:
    print("--- 查看流水 ---")
    if not records:
        print("还没有账目，先去记一笔吧")
        return
    keyword = input("按分类筛选（直接回车显示全部）: ").strip()
    shown = [r for r in records if not keyword or r["category"] == keyword]
    if not shown:
        print(f"没有分类为「{keyword}」的账目。")
        return
    print(f"共 {len(shown)} 笔：")
    for number, record in enumerate(shown, start=1):
        # 当前版本只能记支出（无 type 字段一律视为支出），将来支持收入时补 type="income" 即显示 +
        sign = "+" if record.get("type") == "income" else "-"
        note = f" {record['note']}" if record["note"] else ""
        print(
            f"{number}. {record['time']}  {sign}{record['amount']:.2f} 元"
            f"  [{record['category']}]{note}"
        )


def input_month() -> str:
    """循环询问，直到拿到合法年月（YYYY-MM）；直接回车默认本月。"""
    while True:
        raw = input("年月（如 2026-09，直接回车默认本月）: ").strip()
        if not raw:
            return datetime.now().strftime("%Y-%m")
        try:
            month = datetime.strptime(raw, "%Y-%m")
        except ValueError:
            print("  年月格式不对，请按 2026-09 这样的格式输入。")
            continue
        return month.strftime("%Y-%m")  # 归一化，比如 2026-9 补成 2026-09


def summarize_month(records: list[dict]) -> None:
    print("--- 月度汇总 ---")
    month = input_month()
    matched = [r for r in records if r["time"][:7] == month]
    if not matched:
        print(f"{month} 还没有任何账目。")
        return
    income = sum(r["amount"] for r in matched if r.get("type") == "income")
    expense_by_category: dict[str, float] = {}
    for r in matched:
        if r.get("type") != "income":
            expense_by_category[r["category"]] = (
                expense_by_category.get(r["category"], 0.0) + r["amount"]
            )
    total_expense = sum(expense_by_category.values())
    print(
        f"【{month}】收入：{income:.2f} 元，"
        f"支出：{total_expense:.2f} 元，结余：{income - total_expense:.2f} 元"
    )
    if total_expense == 0:
        print("本月没有支出，没有分类占比。")
        return
    print("各分类支出占比（按金额从高到低）：")
    for category, amount in sorted(
        expense_by_category.items(), key=lambda kv: kv[1], reverse=True
    ):
        print(f"  {category}：{amount:.2f} 元（{amount / total_expense * 100:.1f}%）")


def main() -> None:
    records = load_records()
    print(f"账本已加载，当前共 {len(records)} 笔。")
    while True:
        print()
        print("==== 记账本 ====")
        print("1 记一笔")
        print("2 查看流水")
        print("3 月度汇总")
        print("4 退出")
        choice = input("请选择: ").strip()
        if choice == "1":
            add_record(records)
        elif choice == "2":
            show_records(records)
        elif choice == "3":
            summarize_month(records)
        elif choice == "4":
            print("再见！数据已保存在 data.json。")
            break
        else:
            print(f"没有这个选项：{choice}，请输入 1、2、3 或 4。")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n已退出，数据已保存在 data.json。")

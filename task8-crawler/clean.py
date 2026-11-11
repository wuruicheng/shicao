#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清洗 data_quotes_日期.csv，输出 clean_log.txt。

用法：
    python clean.py                 # 自动找最新的 data_quotes_*.csv
    python clean.py data_quotes_20261111.csv   # 指定输入文件

步骤：
    ① 去重：按 text 全文去重，记录删除条数
    ② 补空：author 空填「未知」，tags 空填「无标签」，分别计数
    ③ 统一格式：text 首尾去空白、内部连续空格压成一个；author_url 补全绝对地址
    ④ 极值校验：各列非空率、text 长度 min/max、长度 <5 的行单独列出

清洗结果另存 data_quotes_clean_日期.csv（utf-8-sig），日志写入 clean_log.txt。
"""

import argparse
import csv
import glob
import os
import re
import sys
from datetime import datetime
from urllib.parse import urljoin

BASE_URL = "https://quotes.toscrape.com"
FIELDS = ["text", "author", "tags", "author_url", "page_num"]

# 同时打印到终端并累积进日志，最后写入 clean_log.txt
_log_lines = []


def log(msg=""):
    print(msg)
    _log_lines.append(msg)


def is_empty(value):
    return value is None or str(value).strip() == ""


def find_input(explicit):
    """返回输入文件路径；显式指定优先，否则取最新的 data_quotes_*.csv。"""
    if explicit:
        if not os.path.exists(explicit):
            return None
        return explicit
    candidates = [
        p for p in glob.glob("data_quotes_*.csv") if "clean" not in os.path.basename(p)
    ]
    return max(candidates, key=os.path.getmtime) if candidates else None


def read_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def non_null_rate(rows, field):
    total = len(rows)
    if total == 0:
        return 0.0, 0
    filled = sum(1 for r in rows if not is_empty(r.get(field)))
    return filled / total * 100, filled


def main():
    parser = argparse.ArgumentParser(description="清洗 data_quotes_日期.csv")
    parser.add_argument("input", nargs="?", help="输入 CSV 路径（默认自动找最新）")
    args = parser.parse_args()

    in_path = find_input(args.input)
    if in_path is None:
        log("错误：未找到输入文件 data_quotes_*.csv")
        return 1

    match = re.search(r"data_quotes_(\d{8})\.csv", os.path.basename(in_path))
    date_str = match.group(1) if match else datetime.now().strftime("%Y%m%d")
    out_path = f"data_quotes_clean_{date_str}.csv"

    rows = read_csv(in_path)
    log(f"读取输入: {in_path}")
    log(f"初始行数: {len(rows)}")

    # ① 去重：按 text 全文去重，保留首次出现
    seen = set()
    deduped = []
    dup_count = 0
    for r in rows:
        key = r.get("text", "")
        if key in seen:
            dup_count += 1
        else:
            seen.add(key)
            deduped.append(r)
    log(
        f"\n[① 去重] 处理前 {len(rows)} 行 -> 处理后 {len(deduped)} 行，删除重复 {dup_count} 条"
    )
    rows = deduped

    # ② 补空
    author_fill = 0
    tags_fill = 0
    for r in rows:
        if is_empty(r.get("author")):
            r["author"] = "未知"
            author_fill += 1
        if is_empty(r.get("tags")):
            r["tags"] = "无标签"
            tags_fill += 1
    log(
        f"\n[② 补空] 行数 {len(rows)}：author 补「未知」{author_fill} 条，"
        f"tags 补「无标签」{tags_fill} 条"
    )

    # ③ 统一格式
    for r in rows:
        r["text"] = re.sub(r"\s+", " ", r.get("text", "")).strip()
        au = r.get("author_url", "")
        if not is_empty(au) and not au.startswith(("http://", "https://")):
            r["author_url"] = urljoin(BASE_URL, au)
    log(f"\n[③ 统一格式] 行数 {len(rows)}：text 去首尾空白并压缩内部空格，author_url 补全绝对地址")

    # ④ 极值校验
    log(f"\n[④ 极值校验] 行数 {len(rows)}（仅校验，不改动行数）")
    log("各列非空率：")
    for field in FIELDS:
        rate, filled = non_null_rate(rows, field)
        log(f"    {field:<10} {rate:6.2f}%  ({filled}/{len(rows)})")

    lengths = [len(r.get("text", "")) for r in rows]
    if lengths:
        min_len = min(lengths)
        max_len = max(lengths)
        log(f"\ntext 长度 min = {min_len}，max = {max_len}，平均 = {sum(lengths) / len(lengths):.2f}")

    short_rows = [r for r in rows if len(r.get("text", "")) < 5]
    log(f"\ntext 长度小于 5 的行共 {len(short_rows)} 条，需人工确认：")
    if short_rows:
        for idx, r in enumerate(short_rows, 1):
            log(f"    [{idx}] text={r.get('text')!r} | author={r.get('author')} | page={r.get('page_num')}")
    else:
        log("    （无）")

    write_csv(out_path, rows)
    log(f"\n清洗结果已保存: {out_path}（共 {len(rows)} 行）")

    with open("clean_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(_log_lines) + "\n")
    log(f"清洗日志已写入: clean_log.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())

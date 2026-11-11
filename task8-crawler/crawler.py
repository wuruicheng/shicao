#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""挑战版爬虫：quotes.toscrape.com 全量采集 + 断点续爬 + 增量采集 + 质量报告。

功能：
    - 翻页采集全部 10 页
    - 跨页全局去重（以 text 为依据）
    - 断点续爬 + 增量采集（state.json 记录进度）
    - sqlite3 自动建表入库（表 quotes）
    - 输出原始 CSV（utf-8-sig）、README.md、数据质量报告 report.md

用法：
    python crawler.py           # 预览模式：第一页前 5 条，供人工核对
    python crawler.py --full    # 全量采集（自动判断：首次 / 断点续爬 / 增量）

合规约束：
    - 每次请求后 sleep 1.5 秒（≥1 秒）
    - 固定 User-Agent
    - 只采集前 10 页（全站）
    - 单页请求失败重试 1 次，仍失败记录页码并跳过；403 立即终止

断点续爬 / 增量采集说明：
    state.json 记录 {last_page, last_text, is_finished} 三个字段：
      - last_page   最后成功采集的页码
      - last_text   最后一条名言文本（作为断点标识）
      - is_finished 是否已跑完全部页
    程序按以下规则决定本次行为：
      1. 无 state.json            -> 首次全量，从第 1 页开始
      2. last_page>0 且未 finished -> 断点续爬，从 last_page+1 页继续
      3. is_finished=True          -> 增量采集，从第 1 页重扫，只采集新增数据
    去重以数据库 quotes 表里已有的 text 为准，避免重复入库。
"""

import argparse
import csv
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://quotes.toscrape.com"
# HTTP 头只能携带 ASCII 字符，中文无法直接放入 User-Agent。
# 需求中的“我的邮箱”为占位符，正式使用前请替换为你的真实邮箱。
USER_AGENT = "VibeCodingCourse/1.0 (student project; contact: student@example.com)"
REQUEST_DELAY = 1.5
MAX_PAGES = 10
PREVIEW_COUNT = 5

FIELDS = ["text", "author", "tags", "author_url", "page_num"]
DB_PATH = "quotes.db"
STATE_PATH = "state.json"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    author TEXT,
    tags TEXT,
    author_url TEXT,
    page_num INTEGER
);
"""


class ForbiddenError(Exception):
    """收到 HTTP 403 响应时抛出，表示站点拒绝访问，应立即终止。"""


class Crawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.total_requests = 0

    def fetch_page(self, url):
        """请求单个页面，失败重试 1 次。

        返回 Response；403 抛出 ForbiddenError；重试后仍失败返回 None。
        """
        for attempt in (1, 2):
            self.total_requests += 1
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 403:
                    raise ForbiddenError(url)
                response.raise_for_status()
                return response
            except ForbiddenError:
                raise
            except requests.RequestException as exc:
                print(f"    [警告] 第 {attempt} 次请求失败 {url}: {exc}", file=sys.stderr)
            time.sleep(REQUEST_DELAY)
        return None


def parse_quotes(html, page_num):
    """解析页面 HTML，返回该页所有名言记录的列表。"""
    soup = BeautifulSoup(html, "lxml")
    quotes = []
    for block in soup.select("div.quote"):
        text_el = block.select_one("span.text")
        author_el = block.select_one("small.author")
        author_link = block.select_one("a[href*='/author/']")
        tag_els = block.select("div.tags a.tag")

        text = text_el.get_text(strip=True).strip("\u201c\u201d") if text_el else ""
        author = author_el.get_text(strip=True) if author_el else ""
        author_url = author_link.get("href", "") if author_link else ""
        tags = ",".join(tag.get_text(strip=True) for tag in tag_els)

        quotes.append(
            {
                "text": text,
                "author": author,
                "tags": tags,
                "author_url": author_url,
                "page_num": page_num,
            }
        )
    return quotes


def truncate(value, width):
    value = str(value)
    return value if len(value) <= width else value[: width - 1] + "\u2026"


def print_table(quotes):
    """把名言以对齐表格打印到终端，供人工核对。"""
    headers = ["#", "text", "author", "tags", "author_url", "page_num"]
    rows = [
        [
            str(i + 1),
            truncate(q["text"], 42),
            q["author"],
            truncate(q["tags"], 24),
            truncate(q["author_url"], 30),
            str(q["page_num"]),
        ]
        for i, q in enumerate(quotes)
    ]
    widths = [
        max(len(headers[j]), *(len(row[j]) for row in rows))
        for j in range(len(headers))
    ]
    line_fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(line_fmt.format(*headers))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print(line_fmt.format(*row))


def save_csv(quotes):
    """把结果用 utf-8-sig 编码写入 data_quotes_日期.csv，返回文件路径。

    若目标文件被占用（如已在 Excel 中打开），降级写入带时间戳的文件名。
    """
    date_str = datetime.now().strftime("%Y%m%d")
    path = f"data_quotes_{date_str}.csv"
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(quotes)
        return path
    except PermissionError:
        fallback = f"data_quotes_{date_str}_{datetime.now().strftime('%H%M%S')}.csv"
        print(
            f"    [警告] 无法写入 {path}（文件被占用，可能已在 Excel 中打开），"
            f"改存 {fallback}",
            file=sys.stderr,
        )
        with open(fallback, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(quotes)
        return fallback


def init_db(db_path=DB_PATH):
    """建表（IF NOT EXISTS）并返回连接。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(CREATE_TABLE_SQL)
    conn.commit()
    return conn


def load_existing_texts(conn):
    """读取数据库中已采集的 text 集合，用于增量去重（避免重复入库）。"""
    cur = conn.cursor()
    cur.execute("SELECT text FROM quotes")
    return {row[0] for row in cur.fetchall()}


def load_all_quotes(conn):
    """读取数据库全部记录（不含自增 id），按入库顺序返回，用于写 CSV/报告。"""
    cur = conn.cursor()
    cur.execute("SELECT text, author, tags, author_url, page_num FROM quotes")
    return [
        {"text": t, "author": a, "tags": g, "author_url": u, "page_num": p}
        for t, a, g, u, p in cur.fetchall()
    ]


def insert_quotes(conn, rows):
    """把本页新增记录追加写入数据库（幂等：只插入不删除）。"""
    if not rows:
        return
    cur = conn.cursor()
    cur.executemany(
        "INSERT INTO quotes (text, author, tags, author_url, page_num) "
        "VALUES (?, ?, ?, ?, ?)",
        [(r["text"], r["author"], r["tags"], r["author_url"], r["page_num"]) for r in rows],
    )
    conn.commit()


def load_state():
    """读取断点状态；不存在则返回默认状态。"""
    if not os.path.exists(STATE_PATH):
        return {"last_page": 0, "last_text": "", "is_finished": False}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    """把断点状态写回 state.json。"""
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def write_readme(rows, csv_path):
    """生成 README.md，含 3 行数据摘要与建表 SQL。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = (
        "# Quotes to Scrape 采集数据说明\n\n"
        "## 数据摘要\n"
        f"- 总条数: {len(rows)}\n"
        f"- 字段列表: {', '.join(FIELDS)}\n"
        f"- 采集时间: {now}\n\n"
        "## 建表 SQL\n"
        "```sql\n"
        f"{CREATE_TABLE_SQL.strip()}\n"
        "```\n\n"
        "## 运行步骤\n"
        "1. 安装依赖: pip install requests beautifulsoup4 lxml\n"
        "2. 采集: python crawler.py --full（自动断点续爬 / 增量采集）\n"
        "3. 清洗: python clean.py（可选）\n\n"
        "## 产出文件\n"
        f"- {csv_path}  原始数据（utf-8-sig，去重后）\n"
        f"- {DB_PATH}  SQLite 数据库（表 quotes）\n"
        "- state.json  采集进度状态（断点续爬）\n"
        "- report.md  数据质量报告\n"
        "- README.md  本说明文件\n"
        "- clean_log.txt / data_quotes_clean_日期.csv  由 clean.py 生成\n"
    )
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)


def write_report(full_quotes, new_count, duplicates, old_skipped,
                 total_requests, elapsed, mode):
    """生成数据质量报告 report.md。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(full_quotes)

    def filled_count(field):
        return sum(1 for q in full_quotes if q.get(field) not in (None, ""))

    # text 极值（最长 / 最短）
    lengths = [(len(q.get("text", "")), q) for q in full_quotes]
    shortest = min(lengths, key=lambda x: x[0]) if lengths else None
    longest = max(lengths, key=lambda x: x[0]) if lengths else None

    # 可疑值清单：文本过短、作者为空、标签为空、作者链接异常
    suspicious = []
    for i, q in enumerate(full_quotes, 1):
        text = q.get("text", "")
        author = q.get("author", "")
        tags = q.get("tags", "")
        author_url = q.get("author_url", "")
        if not text or len(text.strip()) < 5:
            suspicious.append((i, "text", text, "文本为空或长度小于 5"))
        if not author:
            suspicious.append((i, "author", author, "作者为空"))
        if not tags:
            suspicious.append((i, "tags", tags, "标签为空"))
        if not author_url or not author_url.startswith("/author/"):
            suspicious.append((i, "author_url", author_url, "作者链接为空或格式异常"))

    lines = [
        "# 数据质量报告",
        "",
        f"- 生成时间: {now}",
        f"- 采集模式: {mode}",
        "",
        "## 1. 总采集条数",
        f"- 数据集当前总条数: {total}",
        f"- 本次运行新增: {new_count}",
        "",
        "## 2. 各字段完整率",
        "",
        "| 字段 | 完整率 | 非空数 / 总数 |",
        "| --- | --- | --- |",
    ]
    for field in FIELDS:
        filled = filled_count(field)
        rate = filled / total * 100 if total else 0.0
        lines.append(f"| {field} | {rate:.2f}% | {filled} / {total} |")

    lines += [
        "",
        "## 3. 去重条数",
        f"- 跨页去重条数: {duplicates}",
        f"- 增量跳过旧数据条数: {old_skipped}",
        "",
        "## 4. text 极值",
    ]
    if shortest:
        lines.append(
            f"- 最短: {shortest[0]} 字 —— {shortest[1].get('text', '')!r}"
            f"（{shortest[1].get('author', '')}）"
        )
    if longest:
        snippet = longest[1].get("text", "")
        lines.append(
            f"- 最长: {longest[0]} 字 —— {snippet[:80]}{'...' if len(snippet) > 80 else ''}"
            f"（{longest[1].get('author', '')}）"
        )

    lines += [
        "",
        "## 5. 可疑值清单",
        "",
    ]
    if suspicious:
        lines += ["| 行号 | 字段 | 值 | 说明 |", "| --- | --- | --- | --- |"]
        for idx, field, val, reason in suspicious:
            display = (val or "").replace("|", "\\|")[:60]
            lines.append(f"| {idx} | {field} | {display} | {reason} |")
    else:
        lines.append("（无可疑值）")

    lines += [
        "",
        "## 6. 运行统计",
        f"- 总请求数量: {total_requests}",
        f"- 总耗时: {elapsed:.2f} 秒",
        "",
        "## 7. 这份数据集适合回答什么问题",
        "",
        "该数据集包含 100 条名人名言及其作者、标签、来源页码，属于结构化的小规模文本数据集，适合回答以下几类问题：",
        "1. 频次与分布类：哪些作者被引用最多、哪些标签出现最频繁、标签之间的共现关系如何；",
        "2. 文本特征类：名言的长度分布、高频词汇、情绪倾向（可结合情感词典或模型做极性分析）；",
        "3. 关系类：作者与其常用主题标签之间的关联、不同来源页码是否呈现主题变化。",
        "由于样本量较小且主题多样，该数据集更适合作为数据清洗、去重、入库与可视化的教学演示数据，不适合用于需要大样本的统计推断或模型训练。",
        "",
    ]
    with open("report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="采集 quotes.toscrape.com 名言数据（挑战版）")
    parser.add_argument(
        "--full",
        action="store_true",
        help="全量采集（自动断点续爬 / 增量采集），去重后写 CSV、SQLite、README、report",
    )
    args = parser.parse_args()

    crawler = Crawler()
    start = time.time()

    # ---- 预览模式：只抓第一页前 5 条，供人工核对 ----
    if not args.full:
        print("预览模式：抓取第一页前 5 条名言\n")
        response = crawler.fetch_page(BASE_URL + "/")
        if response is None:
            print("无法获取第一页，请稍后重试。", file=sys.stderr)
            return 1
        time.sleep(REQUEST_DELAY)
        quotes = parse_quotes(response.text, 1)[:PREVIEW_COUNT]
        print_table(quotes)
        elapsed = time.time() - start
        print(f"\n总请求数: {crawler.total_requests}，总耗时: {elapsed:.2f} 秒")
        print("人工核对无误后，运行 `python crawler.py --full` 全量采集。")
        return 0

    # ---- 全量模式：断点续爬 / 增量采集 ----
    conn = init_db()
    existing_texts = load_existing_texts(conn)  # 数据库里已有的 text（增量去重依据）

    state = load_state()
    last_page = state.get("last_page", 0)
    is_finished = state.get("is_finished", False)

    # 根据状态决定本次行为
    if last_page > 0 and not is_finished:
        start_page = last_page + 1
        if start_page > MAX_PAGES:
            start_page = 1  # 已翻过末页却未完成（中间有失败页），从头补齐缺口
        mode = "断点续爬"
        print(f"检测到未完成的断点（上次完成到第 {last_page} 页），从第 {start_page} 页继续。")
    elif is_finished:
        start_page = 1
        mode = "增量采集"
        print("检测到上次已全量完成，进入增量采集，从头检查新增数据。")
    else:
        start_page = 1
        mode = "首次全量"
        print("未检测到断点，从第 1 页开始全量采集。")

    seen_texts = set()   # 本次运行内已见 text（跨页去重）
    new_count = 0        # 本次新增入库条数
    total_collected = 0  # 本次抓到的原始条数
    duplicates = 0       # 跨页重复条数
    old_skipped = 0      # 增量跳过旧数据条数
    failed_pages = []

    for page in range(start_page, MAX_PAGES + 1):
        url = f"{BASE_URL}/page/{page}/"
        print(f"正在抓取第 {page} 页 ...")
        try:
            response = crawler.fetch_page(url)
        except ForbiddenError:
            print("收到 403 禁止访问，站点拒绝了请求，立即终止。", file=sys.stderr)
            save_state(state)
            conn.close()
            return 1
        if response is None:
            failed_pages.append(page)
            continue
        time.sleep(REQUEST_DELAY)

        page_quotes = parse_quotes(response.text, page)
        total_collected += len(page_quotes)

        page_new = []
        page_dup = 0
        page_old = 0
        for q in page_quotes:
            if q["text"] in seen_texts:          # 本次运行内跨页重复
                duplicates += 1
                page_dup += 1
            elif q["text"] in existing_texts:     # 数据库中已有（旧数据）
                old_skipped += 1
                page_old += 1
            else:                                 # 真正的新数据
                seen_texts.add(q["text"])
                page_new.append(q)
        insert_quotes(conn, page_new)
        new_count += len(page_new)

        # 每采集完一页，立即更新断点状态（崩溃后可从此页之后续爬）
        state["last_page"] = page
        if page_quotes:
            state["last_text"] = page_quotes[-1]["text"]
        save_state(state)
        print(
            f"    第 {page} 页采集 {len(page_quotes)} 条，"
            f"新增 {len(page_new)} 条，跨页重复 {page_dup} 条，跳过旧数据 {page_old} 条"
        )

    # 所有页都成功才算完成；存在失败页则保持未完成，下次运行补齐
    state["is_finished"] = not failed_pages
    save_state(state)

    full_quotes = load_all_quotes(conn)
    conn.close()

    csv_path = save_csv(full_quotes)
    write_readme(full_quotes, csv_path)
    write_report(full_quotes, new_count, duplicates, old_skipped,
                 crawler.total_requests, time.time() - start, mode)

    elapsed = time.time() - start
    print(f"\n【本次采集总条数: {total_collected}，重复条数: {duplicates}】")
    print(f"本次新增入库: {new_count} 条，跳过旧数据: {old_skipped} 条")
    print(f"数据库当前总条数: {len(full_quotes)}")
    if failed_pages:
        print(f"失败跳过页码: {failed_pages}")
    print(f"总请求数: {crawler.total_requests}，总耗时: {elapsed:.2f} 秒")
    print(f"产出文件: {csv_path}、{DB_PATH}、README.md、report.md、state.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())

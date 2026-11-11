#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""挑战版爬虫：从 quotes.toscrape.com 采集全部 10 页名言，跨页去重后写入 CSV 与 SQLite。

用法：
    python crawler.py           # 预览模式：第一页前 5 条，供人工核对
    python crawler.py --full    # 全量采集全部 10 页，去重 + CSV + SQLite + README

合规约束：
    - 每次请求后 sleep 1.5 秒（≥1 秒）
    - 固定 User-Agent
    - 只采集前 10 页（全站）
    - 单页请求失败重试 1 次，仍失败记录页码并跳过；403 立即终止
    - 跨页全局去重（以 text 为依据）
"""

import argparse
import csv
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


def save_to_db(conn, rows):
    """把去重后的记录写入 SQLite；先清空旧数据，保证重复运行时结果幂等。"""
    cur = conn.cursor()
    cur.execute("DELETE FROM quotes")
    cur.executemany(
        "INSERT INTO quotes (text, author, tags, author_url, page_num) "
        "VALUES (?, ?, ?, ?, ?)",
        [(r["text"], r["author"], r["tags"], r["author_url"], r["page_num"]) for r in rows],
    )
    conn.commit()


def write_readme(rows, total_collected, duplicates, csv_path):
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
        "2. 采集: python crawler.py --full\n\n"
        "## 产出文件\n"
        f"- {csv_path}  原始数据（utf-8-sig，去重后）\n"
        f"- {DB_PATH}  SQLite 数据库（表 quotes）\n"
        "- README.md  本说明文件\n"
        "- clean_log.txt / data_quotes_clean_日期.csv  由 clean.py 清洗生成\n"
    )
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser(description="采集 quotes.toscrape.com 名言数据（挑战版）")
    parser.add_argument(
        "--full",
        action="store_true",
        help="翻页采集全部 10 页，跨页去重后写入 CSV 与 SQLite（默认只预览第一页前 5 条）",
    )
    args = parser.parse_args()

    crawler = Crawler()
    start = time.time()

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

    seen_texts = set()      # 跨页全局去重：保存已见过的 text
    all_quotes = []         # 去重后的最终数据
    total_collected = 0     # 采集到的原始条数（去重前）
    duplicates = 0          # 重复条数
    failed_pages = []

    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}/page/{page}/"
        print(f"正在抓取第 {page} 页 ...")
        try:
            response = crawler.fetch_page(url)
        except ForbiddenError:
            print("收到 403 禁止访问，站点拒绝了请求，立即终止。", file=sys.stderr)
            return 1
        if response is None:
            failed_pages.append(page)
            continue
        time.sleep(REQUEST_DELAY)

        page_quotes = parse_quotes(response.text, page)
        total_collected += len(page_quotes)

        new_quotes = []
        for q in page_quotes:
            if q["text"] in seen_texts:
                duplicates += 1
            else:
                seen_texts.add(q["text"])
                new_quotes.append(q)
        all_quotes.extend(new_quotes)
        print(
            f"    第 {page} 页采集 {len(page_quotes)} 条，"
            f"新增 {len(new_quotes)} 条，重复 {len(page_quotes) - len(new_quotes)} 条"
        )

    csv_path = save_csv(all_quotes)

    conn = init_db()
    save_to_db(conn, all_quotes)
    conn.close()

    write_readme(all_quotes, total_collected, duplicates, csv_path)

    elapsed = time.time() - start

    print(f"\n【本次采集总条数: {total_collected}，重复条数: {duplicates}】")
    print(f"去重后入库条数: {len(all_quotes)}")
    if failed_pages:
        print(f"失败跳过页码: {failed_pages}")
    print(f"总请求数: {crawler.total_requests}，总耗时: {elapsed:.2f} 秒")
    print(f"产出文件: {csv_path}、{DB_PATH}、README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())

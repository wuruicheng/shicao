#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合规爬虫：从 quotes.toscrape.com 采集名言数据。

用法：
    python crawler.py           # 预览模式：只采第一页前 5 条并打印表格，供人工核对
    python crawler.py --full    # 全量模式：翻页采集前 5 页，保存为 CSV

合规约束：
    - 每次请求后 sleep 1.5 秒
    - 固定 User-Agent
    - 只采集前 5 页
    - 单页请求失败重试 1 次，仍失败记录页码并跳过；403 立即终止
"""

import argparse
import csv
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
MAX_PAGES = 5
PREVIEW_COUNT = 5

FIELDS = ["text", "author", "tags", "author_url", "page_num"]


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
    """把结果用 utf-8-sig 编码写入 data_quotes_日期.csv，返回文件路径。"""
    date_str = datetime.now().strftime("%Y%m%d")
    path = f"data_quotes_{date_str}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(quotes)
    return path


def main():
    parser = argparse.ArgumentParser(description="采集 quotes.toscrape.com 名言数据")
    parser.add_argument(
        "--full",
        action="store_true",
        help="翻页采集前 5 页并保存 CSV（默认只预览第一页前 5 条）",
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
        print("人工核对无误后，运行 `python crawler.py --full` 全量采集并保存 CSV。")
        return 0

    all_quotes = []
    failed_pages = []
    for page in range(1, MAX_PAGES + 1):
        url = f"{BASE_URL}/page/{page}/"
        print(f"正在抓取第 {page} 页 ...")
        try:
            response = crawler.fetch_page(url)
        except ForbiddenError:
            print(f"收到 403 禁止访问，站点拒绝了请求，立即终止。", file=sys.stderr)
            return 1
        if response is None:
            failed_pages.append(page)
            continue
        time.sleep(REQUEST_DELAY)
        page_quotes = parse_quotes(response.text, page)
        all_quotes.extend(page_quotes)
        print(f"    第 {page} 页采集 {len(page_quotes)} 条")

    csv_path = save_csv(all_quotes)
    elapsed = time.time() - start

    print(f"\n完成：共采集 {len(all_quotes)} 条名言")
    if failed_pages:
        print(f"失败跳过页码: {failed_pages}")
    print(f"总请求数: {crawler.total_requests}，总耗时: {elapsed:.2f} 秒")
    print(f"结果已保存: {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

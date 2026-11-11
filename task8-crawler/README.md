# Quotes to Scrape 采集数据说明

## 数据摘要
- 总条数: 100
- 字段列表: text, author, tags, author_url, page_num
- 采集时间: 2026-11-11 13:43:04

## 建表 SQL
```sql
CREATE TABLE IF NOT EXISTS quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT,
    author TEXT,
    tags TEXT,
    author_url TEXT,
    page_num INTEGER
);
```

## 运行步骤
1. 安装依赖: pip install requests beautifulsoup4 lxml
2. 采集: python crawler.py --full（自动断点续爬 / 增量采集）
3. 清洗: python clean.py（可选）

## 产出文件
- data_quotes_20261111.csv  原始数据（utf-8-sig，去重后）
- quotes.db  SQLite 数据库（表 quotes）
- state.json  采集进度状态（断点续爬）
- report.md  数据质量报告
- README.md  本说明文件
- clean_log.txt / data_quotes_clean_日期.csv  由 clean.py 生成

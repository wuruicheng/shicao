import pandas as pd

# 文件首部带 UTF-8 BOM，用 utf-8-sig 读取可避免第一列名被污染为 "\ufefftext"
df = pd.read_csv("data_quotes_clean_20261111.csv", encoding="utf-8-sig")

# ---------- 中间过程 ----------
print("总行数:", len(df))
print("author 空值数(NaN):", df["author"].isna().sum())
print("author 空字符串数:", (df["author"] == "").sum())

# ---------- 清洗规则说明 ----------
# 规则: 对 author / tags 做 str.strip()，去掉首尾空白，避免
#       "Albert Einstein" 与 " Albert Einstein " 被当成不同作者。
# 执行前先检测是否真的存在待清洗数据:
author_raw = df["author"]
author_clean = author_raw.str.strip()
tags_raw = df["tags"]
tags_clean = tags_raw.str.strip()
print("author 首尾空白行数:", (author_raw != author_clean).sum())
print("tags   首尾空白行数:", (tags_raw != tags_clean).sum())
print("author 去重后数量: 清洗前", author_raw.nunique(), "| 清洗后", author_clean.nunique())

# 应用清洗(即便本次为 0 行受影响，仍按统一规则执行以保证稳健)
df["author"] = author_clean
df["tags"] = tags_clean

# ---------- 计数 ----------
print("\n== author value_counts 前10 ==")
print(df["author"].value_counts().head(10))

print("\n== 被收录名言最多的作者 前5 ==")
top5 = df["author"].value_counts().head(5)
for i, (name, cnt) in enumerate(top5.items(), 1):
    print(f"{i}. {name}: {cnt} 条")

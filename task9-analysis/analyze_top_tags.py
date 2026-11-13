import pandas as pd

df = pd.read_csv("data_quotes_clean_20261111.csv", encoding="utf-8-sig")

# ---------- 清洗规则说明 ----------
# 规则: 对拆分后的每个标签做 str.strip()，去掉首尾空白，避免
#       " love " 与 "love" 被当成两个不同标签。
# 执行前检测:
raw_exploded = df["tags"].str.split(",").explode()
print("清洗前首尾空白标签数:", (raw_exploded != raw_exploded.str.strip()).sum())
# 应用清洗(本次为 0 行受影响，仍按统一规则执行以保证稳健)
tags = raw_exploded.str.strip()

# ---------- 中间过程 ----------
print("\n原始总记录数:", len(df))
print("展开(explode)后总标签引用数(过滤前):", len(tags))
print("展开后去重标签种类(过滤前):", tags.nunique())

# 脏标签过滤: 不计入主题统计
DIRTY_TAGS = {"无标签", "attributed-no-source"}
dirty_count = tags.isin(DIRTY_TAGS).sum()
print("\n脏标签过滤: 命中", dirty_count, "次",
      "(无标签", (tags == "无标签").sum(), "次 / attributed-no-source",
      (tags == "attributed-no-source").sum(), "次)")
tags_filtered = tags[~tags.isin(DIRTY_TAGS)]
print("展开后总标签引用数(过滤后):", len(tags_filtered))
print("展开后去重标签种类(过滤后):", tags_filtered.nunique())

# ---------- Top10 ----------
total = len(tags_filtered)
vc = tags_filtered.value_counts()
print("\n== Top10 标签 (次数 / 占过滤后总引用 %.2f%%) ==")
for i, (tag, cnt) in enumerate(vc.head(10).items(), 1):
    print(f"{i}. {tag}: {cnt} 次 ({cnt/total*100:.2f}%)")

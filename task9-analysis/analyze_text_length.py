import pandas as pd

df = pd.read_csv("data_quotes_clean_20261111.csv", encoding="utf-8-sig")

# ---------- 清洗规则说明 ----------
# 规则: 对 text 做 str.strip()，去掉首尾空白后再计算长度，
#       避免把首尾空格误算进字符长度。
raw_text = df["text"]
print("清洗前首尾空白行数:", (raw_text != raw_text.str.strip()).sum())
# 应用清洗(本次为 0 行受影响，仍按统一规则执行以保证稳健)
df["text"] = raw_text.str.strip()

df["text_len"] = df["text"].str.len()

# ---------- 中间过程 ----------
print("\n总记录数:", len(df))
print("字符长度均值:", round(df["text_len"].mean(), 2))
print("字符长度中位数:", df["text_len"].median())
print("字符长度最大值:", df["text_len"].max())
print("字符长度最小值:", df["text_len"].min())

# ---------- 分箱频数 ----------
bins = [0, 50, 100, 150, 200, 300, 400, 500, 600, 700, 1200]
labels = ["0-49", "50-99", "100-149", "150-199",
          "200-299", "300-399", "400-499", "500-599",
          "600-699", "700+"]
df["len_bin"] = pd.cut(df["text_len"], bins=bins, labels=labels, right=False)
print("\n== 字符长度分箱频数 ==")
bin_counts = df["len_bin"].value_counts().reindex(labels)
for b, c in bin_counts.items():
    print(f"{b}: {int(c)}")

# ---------- 最长3条 ----------
print("\n== 最长的3条名言 ==")
top3 = df.nlargest(3, "text_len")[["author", "text_len"]]
for i, (_, row) in enumerate(top3.iterrows(), 1):
    print(f"{i}. {row['author']}: {row['text_len']} 字符")

import json

import numpy as np

from index import embed_batch as get_embeddings

with open("index.json", encoding="utf-8") as f:
    chunks = json.load(f)


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(question, chunks, k=3):
    qv = get_embeddings([question])[0]
    scored = sorted(((cosine(qv, c["vec"]), c) for c in chunks),
                    key=lambda x: -x[0])
    return scored[:k]


# 打印 Top5：人工判断找到的块是否真的包含答案
for score, c in search("社团负责人最多可以连任几届？", chunks, k=5):
    print(round(score, 3), c["source"], c["id"], c["text"][:50])

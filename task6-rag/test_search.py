import json

import numpy as np

from index import get_embeddings


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(question, chunks, k=3):
    qv = get_embeddings([question])[0]
    scored = sorted(((cosine(qv, c["vec"]), c) for c in chunks),
                    key=lambda x: -x[0])
    return scored[:k]


with open("data/index_default.json", encoding="utf-8") as f:
    chunks = json.load(f)

# 打印 Top5：人工判断找到的块是否真的包含答案
for score, c in search("报销的时限是多久？", chunks, k=5):
    print(round(score, 3), c["source"], c["id"], c["text"][:50])

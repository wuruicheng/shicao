"""RAG 知识库离线建库脚本。

遍历 docs/ 下的 txt/md 文档，切块后调用 Embedding API 批量生成向量，
结果写入 index.json。仅依赖 numpy + requests + python-dotenv。
"""

import json
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

# ---- 配置 ----
load_dotenv()

EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

SIZE = 400        # 每块字数
OVERLAP = 60      # 相邻块重叠字数
BATCH_SIZE = 32   # 单批最多条数

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
OUTPUT = BASE_DIR / "index.json"


def chunk_text(text, size, overlap):
    """固定长度切分：每块 size 字，相邻块重叠 overlap 字。

    步长为 size - overlap，末块不足 size 也保留；过滤掉纯空白块。
    """
    if size <= overlap:
        raise ValueError(f"size({size}) 必须大于 overlap({overlap})")
    step = size - overlap
    chunks = []
    for start in range(0, len(text), step):
        chunk = text[start:start + size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def load_documents(docs_dir):
    """遍历 docs/ 读取全部 .txt/.md 文件（UTF-8），返回 [(文件名, 文本), ...]。"""
    docs = []
    for path in sorted(docs_dir.iterdir()):
        if path.suffix.lower() not in (".txt", ".md"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            print(f"[警告] 跳过 {path.name}：UTF-8 解码失败（{exc}）")
            continue
        if text.strip():
            docs.append((path.name, text))
    return docs


def embed_batch(texts):
    """调用 Embedding API 嵌入一批文本，返回与输入等长的向量列表（按 index 排序）。"""
    url = EMBEDDING_BASE_URL.rstrip("/") + "/embeddings"
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": EMBEDDING_MODEL, "input": texts}
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in data]


def embed_with_retry(texts):
    """批量嵌入，失败重试一次；仍失败返回 None。"""
    for attempt in (1, 2):
        try:
            return embed_batch(texts)
        except Exception as exc:
            print(f"[警告] 嵌入调用第 {attempt} 次失败：{exc}")
    return None


def self_check(records, docs):
    """自检：所有 vec 长度一致 + 随机抽 3 块与原文一致。"""
    if not records:
        return
    lens = np.array([len(r["vec"]) for r in records])
    if (lens == lens[0]).all():
        print(f"[自检] 向量维度一致：{len(records)} 块均为 {lens[0]} 维")
    else:
        print(f"[自检][警告] 向量维度不一致：min={lens.min()}, max={lens.max()}")
        return

    doc_text = {name: text for name, text in docs}
    samples = random.sample(records, min(3, len(records)))
    ok = True
    for r in samples:
        if r["text"] in doc_text.get(r["source"], ""):
            print(f"[自检] id={r['id']} source={r['source']} 与原文一致 ✓")
        else:
            print(f"[自检][警告] id={r['id']} source={r['source']} 未在原文中命中 ✗")
            ok = False
    if ok:
        print("[自检] 随机抽样一致。")


def main():
    start = time.time()

    if not (EMBEDDING_API_KEY and EMBEDDING_BASE_URL and EMBEDDING_MODEL):
        print("错误：.env 缺少 EMBEDDING_API_KEY / EMBEDDING_BASE_URL / EMBEDDING_MODEL")
        return
    if not DOCS_DIR.exists():
        print(f"错误：找不到 docs 目录 {DOCS_DIR}")
        return

    docs = load_documents(DOCS_DIR)
    if not docs:
        print("警告：docs/ 下没有可读取的 txt/md 文件")
        OUTPUT.write_text(json.dumps([], ensure_ascii=False), encoding="utf-8")
        return

    total_chars = sum(len(text) for _, text in docs)
    chunks = [(source, c) for source, text in docs for c in chunk_text(text, SIZE, OVERLAP)]
    total = len(chunks)
    print(f"读取 {len(docs)} 个文件，总字数 {total_chars}，切出 {total} 块（理论约 {total_chars // (SIZE - OVERLAP)} 块）")

    records = []
    last_reported = 0
    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        vecs = embed_with_retry([text for _, text in batch])
        if vecs is None or len(vecs) != len(batch):
            print(f"[警告] 第 {i}~{i + len(batch) - 1} 块嵌入失败，已跳过 {len(batch)} 块")
            continue
        for (source, text), vec in zip(batch, vecs):
            records.append({
                "id": f"{len(records):06d}",
                "source": source,
                "text": text,
                "vec": [float(x) for x in vec],
            })
        # 每处理 10 块打印一次进度
        while len(records) - last_reported >= 10:
            last_reported += 10
            print(f"进度：已成功嵌入 {last_reported} 块 / 共 {total} 块")

    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    elapsed = time.time() - start
    print(f"完成：共写入 {len(records)} 块（原始 {total} 块），总耗时 {elapsed:.2f} 秒")
    print(f"结果已写入 {OUTPUT}")
    self_check(records, docs)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()

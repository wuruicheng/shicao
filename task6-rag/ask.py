"""命令行 RAG 问答脚本。

加载 index.json，循环接受提问（输入 q 退出）：
- 问题向量化后按余弦相似度检索 Top3，打印来源与分数；
- 将检索结果组装成提示词，调用 deepseek-chat 生成回答。
仅依赖 numpy + requests + python-dotenv，不使用任何 RAG 框架。
"""

import json
import os
import sys
from pathlib import Path

import numpy as np
import requests
from dotenv import load_dotenv

load_dotenv()

# ---- 配置 ----
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek-chat")
CHAT_TEMPERATURE = 0.2

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "index.json"

SYSTEM_PROMPT = "只根据资料回答；资料不足时明确说资料中未找到；末尾用【来源：文件名·块id】标注"


def get_embeddings(texts):
    """调用 Embedding API 生成向量，返回与输入等长的向量列表。"""
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


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def search(question, chunks, k=3):
    """检索 Top-k，返回 [(相似度分数, 块), ...]，按分数降序。"""
    qv = get_embeddings([question])[0]
    scored = sorted(((cosine(qv, c["vec"]), c) for c in chunks),
                    key=lambda x: -x[0])
    return scored[:k]


def build_prompt(question, top):
    """将 Top3 检索结果组装成用户消息。"""
    parts = []
    for i, (_, c) in enumerate(top, 1):
        parts.append(
            f"[{i}] 来源：{c['source']} 块id：{c['id']}\n{c['text']}"
        )
    context = "\n\n".join(parts)
    return f"问题：{question}\n\n资料：\n{context}"


def chat(question, top):
    """调用对话模型生成回答。"""
    url = DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CHAT_MODEL,
        "temperature": CHAT_TEMPERATURE,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(question, top)},
        ],
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def main():
    if not INDEX_PATH.exists():
        print(f"错误：找不到 {INDEX_PATH}，请先运行 index.py 建库。")
        return
    if not (EMBEDDING_API_KEY and EMBEDDING_BASE_URL and EMBEDDING_MODEL):
        print("错误：.env 缺少 Embedding 配置（EMBEDDING_API_KEY/BASE_URL/MODEL）。")
        return
    if not DEEPSEEK_API_KEY:
        print("错误：.env 缺少 DEEPSEEK_API_KEY。")
        return

    chunks = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    print(f"已加载 {len(chunks)} 个文本块。输入问题开始问答，输入 q 退出。\n")

    while True:
        try:
            question = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break
        if question.lower() == "q":
            print("再见。")
            break
        if not question:
            continue

        try:
            top = search(question, chunks, k=3)
        except Exception as exc:
            print(f"检索失败：{exc}\n")
            continue

        print("Top3 检索结果：")
        for i, (score, c) in enumerate(top, 1):
            print(f"  {i}. [{score:.3f}] {c['source']} · id={c['id']} · {c['text'][:60]}…")

        try:
            answer = chat(question, top)
        except Exception as exc:
            print(f"对话失败：{exc}\n")
            continue

        print("\n回答：")
        print(answer)
        print()


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()

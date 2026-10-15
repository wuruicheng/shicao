"""RAG 核心模块：配置、向量化、切块、建库、检索、对话。

供命令行 ask.py、建库脚本 index.py 与 Streamlit 网页 app.py 共用。
仅依赖 numpy + requests + python-dotenv，不使用任何 RAG 框架。
"""

import json
import os
import time
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
DATA_DIR = BASE_DIR / "data"

SIZE = 400        # 每块字数
OVERLAP = 60      # 相邻块重叠字数
BATCH_SIZE = 32   # 单批最多条数

SYSTEM_PROMPT = (
    "仅依据检索资料回答；资料不足时输出“资料中未找到”；"
    "回答末尾用【来源：知识库名｜文件名・块id】标注来源。"
)


def get_embeddings(texts):
    """调用 Embedding API 生成向量，返回与输入等长的向量列表（单批不超过 BATCH_SIZE）。"""
    url = EMBEDDING_BASE_URL.rstrip("/") + "/embeddings"
    headers = {
        "Authorization": f"Bearer {EMBEDDING_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": EMBEDDING_MODEL, "input": texts}
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = sorted(resp.json()["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in data]


def cosine(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def chunk_text(text, size=SIZE, overlap=OVERLAP):
    """固定长度切分：每块 size 字、相邻块重叠 overlap 字，末块保留、过滤纯空白块。"""
    if size <= overlap:
        raise ValueError(f"size({size}) 必须大于 overlap({overlap})")
    step = size - overlap
    return [text[i:i + size] for i in range(0, len(text), step) if text[i:i + size].strip()]


def load_documents(docs_dir):
    """遍历目录读取全部 .txt/.md（UTF-8），返回 [(文件名, 文本), ...]。"""
    docs = []
    for path in sorted(Path(docs_dir).iterdir()):
        if path.suffix.lower() not in (".txt", ".md"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if text.strip():
            docs.append((path.name, text))
    return docs


# ---- 知识库文件管理 ----

def index_path(kb_name):
    """知识库索引文件路径：data/index_{库名}.json。"""
    return DATA_DIR / f"index_{kb_name}.json"


def list_knowledge_bases():
    """列出所有已建知识库名称（按名称排序）。"""
    if not DATA_DIR.exists():
        return []
    return sorted(p.stem[len("index_"):] for p in DATA_DIR.glob("index_*.json"))


def load_index(kb_name):
    """读取指定知识库的块列表。"""
    return json.loads(index_path(kb_name).read_text(encoding="utf-8"))


def build_index(kb_name, docs_dir, progress=None):
    """为指定知识库建库，写入 data/index_{库名}.json。

    progress(done, total) 为可选进度回调，切块后与每批嵌入后各调用一次。
    返回 (块数, 总字数, 耗时秒)。
    """
    start = time.time()
    docs = load_documents(docs_dir)
    if not docs:
        raise ValueError(f"{docs_dir} 下没有可读取的 txt/md 文件")

    chunks = [(source, c) for source, text in docs for c in chunk_text(text)]
    total = len(chunks)
    if progress:
        progress(0, total)

    records = []
    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        vecs = None
        for attempt in (1, 2):
            try:
                vecs = get_embeddings([t for _, t in batch])
                break
            except Exception as exc:
                print(f"[警告] 第 {i}~{i + len(batch) - 1} 块嵌入第 {attempt} 次失败：{exc}")
        if vecs is None or len(vecs) != len(batch):
            print(f"[警告] 跳过第 {i} 批（{len(batch)} 块）")
            if progress:
                progress(len(records), total)
            continue
        for (source, text), vec in zip(batch, vecs):
            records.append({
                "id": f"{len(records):06d}",
                "source": source,
                "text": text,
                "vec": [float(x) for x in vec],
            })
        if progress:
            progress(len(records), total)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    index_path(kb_name).write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return len(records), sum(len(t) for _, t in chunks), time.time() - start


# ---- 检索与对话 ----

def search(question, kb_names, k=3):
    """在指定知识库（单个或多个）中检索 Top-k。

    跨库时合并所有库的结果按余弦分数重排取全局 Top-k；每条结果附带 kb 字段。
    返回 [(分数, 块), ...]。
    """
    qv = get_embeddings([question])[0]
    scored = []
    for kb in kb_names:
        for c in load_index(kb):
            item = {**c, "kb": kb}
            scored.append((cosine(qv, c["vec"]), item))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


def build_prompt(question, top):
    """将检索结果组装成用户消息。"""
    parts = []
    for i, (_, c) in enumerate(top, 1):
        parts.append(f"[{i}] 来源：{c['kb']}｜{c['source']}・{c['id']}\n{c['text']}")
    return f"问题：{question}\n\n资料：\n" + "\n\n".join(parts)


def chat(question, top, stream=False):
    """调用对话模型生成回答。stream=True 时返回逐段字符串生成器。"""
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
        "stream": stream,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120, stream=stream)
    resp.raise_for_status()

    if not stream:
        return resp.json()["choices"][0]["message"]["content"]

    def gen():
        for line in resp.iter_lines():
            line = line.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0]["delta"].get("content", "")
            except Exception:
                continue
            if delta:
                yield delta

    return gen()

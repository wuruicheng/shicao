"""命令行建库脚本。

用法：
    python index.py                    # 建默认库 default → data/index_default.json
    python index.py --kb 章程          # 自定义库名 → data/index_章程.json
    python index.py --kb 章程 --docs my_docs
"""

import argparse
import sys

from rag_core import build_index, get_embeddings  # noqa: F401  # get_embeddings 供 test_search 等复用


def main():
    parser = argparse.ArgumentParser(description="构建 RAG 知识库索引")
    parser.add_argument("--kb", default="default", help="知识库名称（决定 data/index_{库名}.json）")
    parser.add_argument("--docs", default="docs", help="文档目录")
    args = parser.parse_args()

    def progress(done, total):
        print(f"进度：已嵌入 {done}/{total} 块")

    try:
        n, chars, elapsed = build_index(args.kb, args.docs, progress=progress)
    except ValueError as exc:
        print(f"错误：{exc}")
        sys.exit(1)

    print(f"完成：知识库「{args.kb}」共 {n} 块 / 总字数 {chars}，总耗时 {elapsed:.2f} 秒")
    print(f"已写入 data/index_{args.kb}.json")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    main()

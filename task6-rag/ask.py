"""命令行 RAG 问答脚本。

用法：
    python ask.py                    # 检索默认库 default
    python ask.py --kb 章程          # 检索单个知识库
    python ask.py --all              # 跨库检索（合并全部知识库）
    python ask.py --all --k 5        # 跨库 + Top5
输入 q 退出。
"""

import argparse
import sys

from rag_core import chat, list_knowledge_bases, search


def main():
    parser = argparse.ArgumentParser(description="命令行 RAG 问答")
    parser.add_argument("--kb", default="default", help="单个知识库名称（默认 default）")
    parser.add_argument("--all", action="store_true", help="跨库检索（合并全部知识库）")
    parser.add_argument("--k", type=int, default=3, help="检索 Top-k（默认 3）")
    args = parser.parse_args()

    available = list_knowledge_bases()
    if args.all:
        kb_names = available
        if not kb_names:
            print("错误：还没有任何知识库，请先运行 index.py 建库。")
            return
        print(f"跨库检索模式：{len(kb_names)} 个知识库（{', '.join(kb_names)}）")
    else:
        if args.kb not in available:
            print(f"错误：知识库「{args.kb}」不存在，可用：{available or '无'}。")
            return
        kb_names = [args.kb]
        print(f"知识库：{args.kb}")

    print("输入问题开始问答，输入 q 退出。\n")
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
            top = search(question, kb_names, k=args.k)
        except Exception as exc:
            print(f"检索失败：{exc}\n")
            continue

        print(f"Top{args.k} 检索结果：")
        for i, (score, c) in enumerate(top, 1):
            print(f"  {i}. [{score:.3f}] {c['kb']}｜{c['source']}・{c['id']} · {c['text'][:50]}…")

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

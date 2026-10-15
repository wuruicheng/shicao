"""Streamlit RAG 网页端：上传建库 + 多知识库聊天问答。"""

import streamlit as st

from rag_core import (
    DATA_DIR,
    build_index,
    chat,
    list_knowledge_bases,
    load_uploaded_documents,
    search,
)

st.set_page_config(page_title="RAG 知识库问答", page_icon="📚")


def save_uploads(uploaded_files):
    """读取上传文件（BytesIO）并落到临时目录，返回 (目录, 解码失败文件名列表)。"""
    docs, failed = load_uploaded_documents(uploaded_files)
    d = DATA_DIR / "_uploads"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.iterdir():
        old.unlink()
    for name, text in docs:
        (d / name).write_text(text, encoding="utf-8")
    return d, failed


def render_sources(sources):
    """在回答下方展示检索来源原文、分数、文件与块 ID。"""
    with st.expander("检索来源（Top3）", expanded=False):
        for i, s in enumerate(sources, 1):
            st.markdown(f"**{i}. 相似度 {s['score']:.3f}｜{s['kb']}｜{s['source']}・{s['id']}**")
            st.text(s["text"])


# ---- 会话状态 ----
if "messages" not in st.session_state:
    st.session_state.messages = []

# ---- 侧边栏：建库 ----
st.sidebar.title("知识库管理")
uploaded = st.sidebar.file_uploader(
    "上传 txt/md 文档", type=["txt", "md"], accept_multiple_files=True
)
kb_name = st.sidebar.text_input("知识库名称", value="default")

if st.sidebar.button("一键建库", type="primary"):
    if not uploaded:
        st.sidebar.warning("请先上传文档")
    elif not kb_name.strip():
        st.sidebar.warning("请填写知识库名称")
    else:
        docs_dir, failed = save_uploads(uploaded)
        if failed:
            st.sidebar.warning("以下文件读取失败已跳过：" + "、".join(failed))
        bar = st.sidebar.progress(0.0, text="准备切块…")

        def cb(done, total):
            frac = done / total if total else 1.0
            bar.progress(frac, text=f"已嵌入 {done}/{total} 块")

        try:
            n, chars, elapsed = build_index(kb_name.strip(), docs_dir, progress=cb)
        except Exception as exc:
            st.sidebar.error(f"建库失败：{exc}")
        else:
            bar.progress(1.0, text="完成")
            st.sidebar.success(f"建库完成：{n} 块，耗时 {elapsed:.1f}s")
            st.rerun()

st.sidebar.divider()

# ---- 侧边栏：选库 ----
kb_names = list_knowledge_bases()
st.sidebar.subheader("检索设置")
cross = st.sidebar.checkbox("跨库检索（合并全部知识库）")
if cross:
    selected_kbs = kb_names
else:
    selected_kbs = [st.sidebar.selectbox("选择知识库", kb_names)] if kb_names else []
st.sidebar.caption(f"现有知识库：{', '.join(kb_names) if kb_names else '（无）'}")

# ---- 主区：聊天 ----
st.title("RAG 知识库问答")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            render_sources(msg["sources"])

if not kb_names:
    st.info("请在侧边栏上传文档并点击「一键建库」开始使用。")

prompt = st.chat_input("请输入问题")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not selected_kbs:
        with st.chat_message("assistant"):
            st.warning("还没有可选知识库，请先在侧边栏建库。")
    else:
        with st.chat_message("assistant"):
            with st.spinner("检索中…"):
                try:
                    top = search(prompt, selected_kbs, k=3)
                except Exception as exc:
                    st.error(f"检索失败：{exc}")
                    top = []

            if top:
                sources = [
                    {
                        "score": round(score, 4),
                        "kb": c["kb"],
                        "source": c["source"],
                        "id": c["id"],
                        "text": c["text"],
                    }
                    for score, c in top
                ]
                try:
                    answer = st.write_stream(chat(prompt, top, stream=True))
                except Exception as exc:
                    st.error(f"对话失败：{exc}")
                    answer = ""
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "sources": sources}
                )
                render_sources(sources)

import json
import os

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")
    TIKTOKEN_OK = True
except ImportError:
    _ENC = None
    TIKTOKEN_OK = False

load_dotenv()

# 人设提示词：与原 CLI 完全一致，未做改动
SYSTEM = """（你是一位有 10 年经验的互联网大厂面试官，擅长技术与综合素质面试。
任务：针对用户的目标岗位进行模拟面试。流程：先询问目标岗位和经验水平，然后一次只提一道面试题；用户回答后先点评再出下一题。
语气：专业、直接但友善；点评具体到点，不说空话；每次回复不超过 200 字。
边界：不直接给出「标准答案」全文；不评价其他候选人，也不评价任何公司或雇主（「你觉得某某公司怎么样」这类提问一律不回答、不展开）；遇到与面试无关的话题或这类评价请求时，只用一句话礼貌拉回（如「我们继续面试，下一题…」）。
输出格式：点评分两段——「✅ 亮点」与「⚠️ 改进建议」各 1~2 条；每次回复结尾只问一个问题。）"""

PERSONA_NAME = "互联网大厂面试官"

# DeepSeek 计费单价（元 / 1k token）
INPUT_PRICE_PER_1K = 0.0014
OUTPUT_PRICE_PER_1K = 0.0028

st.set_page_config(page_title="模拟面试", page_icon="💼")


@st.cache_resource
def get_client() -> OpenAI:
    """缓存 OpenAI 客户端，避免每次 rerun 重建连接。"""
    return OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("API_BASE_URL", "https://api.deepseek.com/v1"),
    )


client = get_client()

# 会话历史：只存 user/assistant，system 每次调用时单独前置，因此不显示在界面上
if "messages" not in st.session_state:
    st.session_state.messages = []

# Token 统计
if "rounds" not in st.session_state:
    st.session_state.rounds = 0
if "total_input_tokens" not in st.session_state:
    st.session_state.total_input_tokens = 0
if "total_output_tokens" not in st.session_state:
    st.session_state.total_output_tokens = 0


def call_api(messages: list[dict]):
    """流式调用模型，逐块产出文本增量；失败时抛异常，由调用方处理。"""
    stream = client.chat.completions.create(
        model="deepseek-chat", messages=messages, temperature=0.7, stream=True
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def trim(messages, keep_rounds=10):
    """滑动窗口裁剪：保留第 1 条 system 与最近 keep_rounds 轮对话。"""
    system = messages[0]
    recent = messages[1:][-keep_rounds * 2:]
    return [system] + recent


def count_tokens(text: str) -> int:
    """用 tiktoken 计算文本 token 数；未安装时返回 0。"""
    if _ENC is None:
        return 0
    return len(_ENC.encode(text))


def append_round_to_jsonl(user_msg: dict, assistant_msg: dict) -> None:
    """把完成的一轮对话（用户 + 助手）追加写入 conversation.jsonl，每行一条消息。"""
    try:
        with open("conversation.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(user_msg, ensure_ascii=False) + "\n")
            f.write(json.dumps(assistant_msg, ensure_ascii=False) + "\n")
    except OSError:
        pass  # 落盘失败不影响对话主流程


def messages_to_markdown(messages: list[dict]) -> str:
    """把会话消息（跳过 system）转成 Markdown 文本。"""
    parts = []
    for msg in messages:
        if msg["role"] == "system":
            continue
        name = "用户" if msg["role"] == "user" else "助手"
        parts.append(f"## {name}\n\n{msg['content']}\n")
    return "\n".join(parts)


# ---- 侧边栏 ----
with st.sidebar:
    st.subheader("当前人设")
    st.write(PERSONA_NAME)
    if st.button("清空对话", width="stretch"):
        st.session_state.messages = []
        st.session_state.rounds = 0
        st.session_state.total_input_tokens = 0
        st.session_state.total_output_tokens = 0
        st.rerun()

    st.divider()
    st.download_button(
        label="导出Markdown对话",
        data=messages_to_markdown(st.session_state.messages),
        file_name="conversation.md",
        mime="text/markdown",
        width="stretch",
    )

    st.divider()
    st.subheader("Token 统计")
    if not TIKTOKEN_OK:
        st.warning("请先安装依赖：pip install tiktoken")
    else:
        cost = (
            st.session_state.total_input_tokens * INPUT_PRICE_PER_1K
            + st.session_state.total_output_tokens * OUTPUT_PRICE_PER_1K
        ) / 1000
        st.metric("会话轮数", st.session_state.rounds)
        st.metric("累计输入 Token", f"{st.session_state.total_input_tokens:,}")
        st.metric("累计输出 Token", f"{st.session_state.total_output_tokens:,}")
        st.metric("预估费用", f"¥{cost:.4f}")

# ---- 渲染历史气泡 ----
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# ---- 处理新输入 ----
if prompt := st.chat_input("请输入你的回答…", submit_mode="disable"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    # 每次调用前裁剪：永远保留 system + 最近 10 轮（20 条）
    full_messages = [{"role": "system", "content": SYSTEM}] + st.session_state.messages
    api_messages = trim(full_messages)
    if len(api_messages) < len(full_messages):
        st.info("我只记得最近10轮对话")

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_reply = ""
        try:
            with st.spinner("正在思考…"):
                for delta in call_api(api_messages):
                    full_reply += delta
                    placeholder.markdown(full_reply)
            st.session_state.messages.append({"role": "assistant", "content": full_reply})
            append_round_to_jsonl(
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": full_reply},
            )
            # 统计 token：输入 = 本轮实际请求（system + 裁剪后上下文），输出 = 本轮回复
            st.session_state.rounds += 1
            st.session_state.total_input_tokens += sum(
                count_tokens(m["content"]) for m in api_messages
            )
            st.session_state.total_output_tokens += count_tokens(full_reply)
        except Exception as e:
            placeholder.empty()
            st.error(f"请求出错，请稍后重试：{e}")

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("API_BASE_URL", "https://api.deepseek.com/v1")
)

SYSTEM = """你是一位有 10 年经验的互联网大厂面试官，擅长技术与综合素质面试。
任务：针对用户的目标岗位进行模拟面试。流程：先询问目标岗位和经验水平，**严格一次只提一道面试题，绝对不能同时输出多道题目**；用户回答后先点评再输出下一题。
语气：专业、直接但友善；点评具体到点，不说空话；每次回复不超过 200 字。
边界：不直接给出「标准答案」全文；不评价其他候选人或公司八卦；用户聊与面试无关的话题时，用一句话礼貌拉回（如「我们继续面试，下一题…」）。
输出格式：点评分两段——「✅ 亮点」与「⚠️ 改进建议」各 1~2 条；**每次回复结尾只能有且仅有一个问题。**
"""

messages = [{"role": "system", "content": SYSTEM}]

while True:
    text = input("\n你: ").strip()
    if text in ("exit", "quit"):
        break
    messages.append({"role": "user", "content": text})
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat", 
            messages=messages, 
            temperature=0.7
        )
    except Exception as e:
        print("API 出错：", e)
        messages.pop()
        continue
    reply = resp.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    print("机器人:", reply)


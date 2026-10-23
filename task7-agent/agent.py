import re
import json
import os
import datetime
from openai import OpenAI
from dotenv import load_dotenv

# ===================== 工具函数（放最前面！）=====================
def calculate(expression: str) -> str:
    """四则运算：只允许数字与 + - * / ( ) 和小数点"""
    if not re.fullmatch(r"[0-9+\-*/(). ]+", expression):
        return "错误：表达式包含非法字符，只支持四则运算"
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"错误：无法计算（{e}）"


WEATHER_DB = {
    "北京": {"temp": 21, "cond": "晴"},
    "上海": {"temp": 26, "cond": "多云"},
    "广州": {"temp": 30, "cond": "雷阵雨"},
}

def get_weather(city: str) -> str:
    if not isinstance(city, str) or not city.strip():
        return "错误：city 必须是非空字符串"
    data = WEATHER_DB.get(city.strip())
    if not data:
        return f"错误：暂无 {city} 的天气数据，可查询：{'、'.join(WEATHER_DB)}"
    return f"{city}当前{data['cond']}，气温{data['temp']}℃"


def get_datetime() -> str:
    """返回当前本地日期与时间（含星期）。"""
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    now = datetime.datetime.now()
    return now.strftime(f"%Y-%m-%d %H:%M:%S 星期{weekdays[now.weekday()]}")


# ===================== 文件整理：白名单与安全校验 =====================
WHITELIST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_files")
MOVE_RECORDS = []  # 记录每一条移动（源 → 目标），供最终报告使用

def _resolve_in_whitelist(path: str):
    """安全校验核心：把路径规范化为绝对路径并校验是否位于白名单内。

    相对路径以白名单根目录为基准，经 realpath 消解 .. 与符号链接后再校验前缀，
    防止越界访问白名单之外的文件。在白名单内返回绝对路径，否则返回 None。
    """
    root = os.path.realpath(WHITELIST_DIR)
    candidate = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    if candidate == root or candidate.startswith(root + os.sep):
        return candidate
    return None


def scan_files() -> str:
    """扫描白名单文件夹，返回所有文件的相对路径、后缀、修改时间。"""
    root = WHITELIST_DIR
    if not os.path.isdir(root):
        return f"错误：白名单文件夹不存在：{root}"
    lines = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if _resolve_in_whitelist(full) is None:  # 【安全校验】防御越界
                continue
            rel = os.path.relpath(full, root)
            ext = os.path.splitext(fn)[1] or "（无后缀）"
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M:%S")
            lines.append(f"{rel} | 后缀：{ext} | 修改时间：{mtime}")
    if not lines:
        return "白名单文件夹为空，没有文件。"
    return "\n".join(lines)


def move_file(source: str, target_dir: str) -> str:
    """把 source 文件移动到 target_dir 分类文件夹（自动创建目标文件夹）。

    源与目标路径都必须位于白名单内，否则拒绝操作。
    """
    # 【安全校验】源路径必须在白名单内
    src = _resolve_in_whitelist(source)
    if src is None:
        return f"错误：源文件不在白名单内，已拒绝操作：{source}"
    # 【安全校验】目标路径必须在白名单内
    dst_dir = _resolve_in_whitelist(target_dir)
    if dst_dir is None:
        return f"错误：目标路径不在白名单内，已拒绝操作：{target_dir}"

    if not os.path.isfile(src):
        return f"错误：源文件不存在：{source}"

    os.makedirs(dst_dir, exist_ok=True)  # 自动创建分类文件夹
    dst = os.path.join(dst_dir, os.path.basename(src))
    if os.path.abspath(src) == os.path.abspath(dst):
        return f"跳过：{source} 已在目标位置，无需移动。"

    base, ext = os.path.splitext(dst)
    i = 1
    while os.path.exists(dst):  # 同名冲突自动加序号，避免覆盖
        dst = f"{base}_{i}{ext}"
        i += 1

    os.rename(src, dst)  # 原生 os 移动（同盘，不使用 shutil）

    rel_src = os.path.relpath(src, WHITELIST_DIR)
    rel_dst = os.path.relpath(dst, WHITELIST_DIR)
    record = f"{rel_src} → {rel_dst}"
    MOVE_RECORDS.append(record)
    return f"移动成功：{record}"


# ===================== 加载密钥、初始化客户端 =====================
load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

# ===================== 注册工具Schema、调度字典（重新手打干净版本） =====================
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "计算四则运算表达式。当需要精确算术（加减乘除、括号）时使用，不要自己心算。",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "合法四则运算表达式，如 (3+5)*2.5"
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市当前天气（气温与天气状况）。涉及天气的问题必须调用本工具，禁止凭记忆回答。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名，如：北京"
                    }
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_datetime",
            "description": "获取当前本地日期和时间（含星期）。当用户询问今天/现在的日期、时间或星期几时使用，禁止凭记忆回答。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_files",
            "description": "扫描白名单文件夹，返回所有文件的相对路径、后缀和修改时间。整理文件前必须先调用本工具获取文件列表。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "把白名单内的一个文件移动到分类子文件夹（自动创建目标文件夹）。source 与 target_dir 都必须是白名单内的相对路径，移动前已经过人工确认。",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "要移动的文件相对路径，如 报告.pdf"},
                    "target_dir": {"type": "string", "description": "目标分类文件夹相对路径，如 pdf"}
                },
                "required": ["source", "target_dir"]
            }
        }
    }
]

TOOL_FUNCS = {
    "calculate": calculate,
    "get_weather": get_weather,
    "get_datetime": get_datetime,
    "scan_files": scan_files,
    "move_file": move_file,
}

# ===================== 系统提示词 =====================
system_msg = "你是会调用工具完成任务的助手。需要精确计算或实时数据时必须调用工具，禁止凭空编造。"

# ===================== Token 统计与费用估算 =====================
# 全局累计 token（会话级，跨任务累计）
TOKEN_STATS = {"prompt": 0, "completion": 0, "total": 0}

# deepseek-chat 公开单价（元 / 百万 token），价格可能随官方调整，按需修改
PRICE_INPUT_PER_M = 2.0    # 输入（缓存未命中）
PRICE_OUTPUT_PER_M = 8.0   # 输出

def _record_usage(usage, label: str = "") -> None:
    """读取 usage，累计全局 token，实时打印本次与累计 token 及估算费用。"""
    if usage is None:
        print("（本次调用无 usage 信息）")
        return
    prompt = getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", 0) or 0

    TOKEN_STATS["prompt"] += prompt
    TOKEN_STATS["completion"] += completion
    TOKEN_STATS["total"] += prompt + completion

    call_cost = (prompt * PRICE_INPUT_PER_M + completion * PRICE_OUTPUT_PER_M) / 1_000_000
    total_cost = (TOKEN_STATS["prompt"] * PRICE_INPUT_PER_M
                  + TOKEN_STATS["completion"] * PRICE_OUTPUT_PER_M) / 1_000_000

    print(f"💰 {label} token：输入 {prompt} / 输出 {completion}，本次估算费用 ¥{call_cost:.6f}")
    print(f"   累计 token：输入 {TOKEN_STATS['prompt']} / 输出 {TOKEN_STATS['completion']}"
          f" / 合计 {TOKEN_STATS['total']}，累计估算费用 ¥{total_cost:.6f}")

# ===================== 单轮 Function Calling 测试函数 =====================
def single_round_test():
    messages = [
        {"role": "system", "content": "你是会调用工具完成任务的助手。需要精确计算或实时数据时必须调用工具，禁止凭空编造。"},
        {"role": "user", "content": "北京现在多少度？(3+5)*2.5 等于多少？"},
    ]
    # 第一次请求：模型决定要不要调用工具
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        tools=tools,
        temperature=0.3
    )
    msg = resp.choices[0].message
    print("\n=====第一轮：模型工具调用请求=====")
    print("模型是否要调用工具:", bool(msg.tool_calls))

    # 把模型这条assistant消息先加入对话
    messages.append(msg)

    if msg.tool_calls:
        for tc in msg.tool_calls:
            print(f"→ 调用工具：{tc.function.name}，原始参数：{tc.function.arguments}")
            # 解析参数，容错
            try:
                args = json.loads(tc.function.arguments)
            except Exception as e:
                tool_result = f"参数JSON解析失败：{str(e)}"
            else:
                func = TOOL_FUNCS[tc.function.name]
                tool_result = func(**args)
            print(f"→ 工具返回结果：{tool_result}")
            # 包装tool消息，追加进对话
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": tool_result
            })
        # 第二次请求：把工具结果回传给模型，让它写最终回答
        print("\n=====第二轮：回传工具结果，请求最终回答=====")
        resp2 = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            temperature=0.3
        )
        final_msg = resp2.choices[0].message
        print("✅ 最终回答：")
        print(final_msg.content)
    else:
        # 模型直接给答案，不需要工具
        print("✅ 模型直接回答：")
        print(msg.content)

# ===================== 手写 Agent 循环骨架 =====================
def run_agent(task: str, max_iterations: int = 8) -> str:
    """多轮 Agent 循环：反复请求模型，直到模型给出最终回答或达到步数上限。

    安全机制：①最大迭代上限 ②JSON解析容错 ③工具存在性校验 ④运行日志打印。
    """
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": task},
    ]

    for step in range(1, max_iterations + 1):
        # 请求模型
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            temperature=0.3,
        )
        msg = resp.choices[0].message
        # Token 统计：每次模型调用后读取 usage 并累计（标注位置）
        _record_usage(resp.usage, f"第{step}轮")
        # 每次 assistant 消息都必须 append 进 messages
        messages.append(msg)

        # 没有 tool_calls：任务完成，打印步数并直接返回模型回答
        if not msg.tool_calls:
            print(f"✅ 第 {step} 轮完成，模型给出最终回答。")
            return msg.content or ""

        # 逐个执行模型请求的工具
        for tc in msg.tool_calls:
            name = tc.function.name
            raw_args = tc.function.arguments

            # 安全机制①：JSON 解析容错
            try:
                args = json.loads(raw_args or "{}")
            except json.JSONDecodeError as e:
                tool_result = f"工具参数 JSON 解析失败：{e}"
            else:
                # 安全机制②：工具存在性校验
                func = TOOL_FUNCS.get(name)
                if func is None:
                    tool_result = f"错误：未知工具 {name}"
                else:
                    tool_result = func(**args)

            # 安全机制③：运行日志打印（轮次、工具名、参数、返回结果）
            print(f"[第{step}轮] 调用工具：{name} | 参数：{raw_args} | 返回结果：{tool_result}")

            # 组装 role="tool" 消息，带上 tool_call_id
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": name,
                "content": str(tool_result),
            })

    # 安全机制④：达到最大迭代上限
    return "已达到最大步数上限，任务中止。"

# ===================== 文件整理编排（含人工确认门禁） =====================
def organize_files(instruction: str) -> None:
    """文件整理流程：扫描 → 生成方案 → 人工确认 → 执行移动 → 输出报告。

    复用 run_agent 的全部容错机制（迭代上限/JSON容错/未知工具/步骤日志），
    并在“生成方案”与“执行移动”两段之间插入【人工确认门禁】。
    """
    # 阶段1：扫描 + 生成分类方案（只规划，禁止移动）
    plan_task = (
        "请先调用 scan_files 扫描白名单文件夹，"
        "然后生成按文件扩展名分组的整理方案，逐条列出每个文件应移动到哪个子文件夹。"
        "本阶段只做规划，禁止调用 move_file。"
    )
    print("\n[阶段1] 扫描并生成整理方案...")
    plan = run_agent(plan_task)
    if not plan:
        print("⚠️ 未获取到方案，终止整理。")
        return

    print("\n" + "=" * 50)
    print("拟执行整理方案如下：")
    print(plan)
    print("=" * 50)

    # 【安全门禁】人工确认：只有输入 y 才继续，其它任意字符终止
    confirm = input("确认执行移动？输入 y 继续，其它任意字符终止本次整理：").strip().lower()
    if confirm != "y":
        print("❌ 已终止本次整理，未执行任何文件操作。")
        return

    # 阶段2：执行移动 + 输出报告
    execute_task = (
        "请执行已确认的整理方案。先再次调用 scan_files 获取当前文件列表，"
        "然后对每个文件调用 move_file 移动到对应的分类子文件夹。"
        "全部移动完成后，输出整理报告，逐条列出每个文件的移动记录。\n\n"
        f"已确认的方案：\n{plan}"
    )
    print("\n[阶段2] 执行移动...")
    report = run_agent(execute_task, max_iterations=12)

    # 权威报告以 MOVE_RECORDS 为准，防止模型幻觉
    print("\n" + "=" * 50)
    print("📋 整理报告（实际移动记录）：")
    if MOVE_RECORDS:
        for i, rec in enumerate(MOVE_RECORDS, 1):
            print(f"  {i}. {rec}")
    else:
        print("  （无移动记录）")
    print("=" * 50)
    if report:
        print("Agent 总结：", report)


def _ensure_test_files() -> None:
    """创建白名单文件夹并放入几个示例文件（仅测试用，可删除）。"""
    os.makedirs(WHITELIST_DIR, exist_ok=True)
    samples = ["会议记录.txt", "readme.txt", "app.py", "数据.xlsx", "报告.pdf", "照片.jpg"]
    for name in samples:
        path = os.path.join(WHITELIST_DIR, name)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"示例文件：{name}\n")

# ===================== 程序入口（CLI 交互模式） =====================
if __name__ == "__main__":
    _ensure_test_files()  # 测试用：创建白名单并放入示例文件
    print("=" * 50)
    print("多工具 Agent：calculate / get_weather / get_datetime / scan_files / move_file")
    print("输入任务开始对话；输入含“整理”的指令触发文件整理；输入 exit 退出。")
    print("=" * 50)

    while True:
        task = input("\n你：").strip()
        if task.lower() == "exit":
            total_cost = (TOKEN_STATS["prompt"] * PRICE_INPUT_PER_M
                          + TOKEN_STATS["completion"] * PRICE_OUTPUT_PER_M) / 1_000_000
            print(f"👋 再见！本会话累计 token：输入 {TOKEN_STATS['prompt']} / 输出 {TOKEN_STATS['completion']}"
                  f" / 合计 {TOKEN_STATS['total']}，累计估算费用 ¥{total_cost:.6f}")
            break
        if not task:
            print("⚠️ 输入为空，请重新输入。")
            continue
        if "整理" in task:
            organize_files(task)  # 文件整理流程（含人工确认门禁）
        else:
            answer = run_agent(task)
            print("🤖 Agent：", answer)

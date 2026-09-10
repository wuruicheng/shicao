import random
from datetime import datetime

MAX_TRIES = 7
SCORE_FILE = "scores.txt"


def read_guess(count):
    while True:
        text = input(f"第 {count}/{MAX_TRIES} 次猜测，请输入你的猜测：").strip()
        try:
            guess = int(text)
        except ValueError:
            print("请输入 1~100 之间的整数")
            continue
        if 1 <= guess <= 100:
            return guess
        print("请输入 1~100 之间的整数")


def play_round():
    answer = random.randint(1, 100)
    print(f"我想好了一个 1~100 的整数，最多可以猜 {MAX_TRIES} 次。")
    for count in range(1, MAX_TRIES + 1):
        guess = read_guess(count)
        if guess < answer:
            print("小了。")
        elif guess > answer:
            print("大了。")
        else:
            print(f"猜对了！你一共猜了 {count} 次。")
            return True, count
    print(f"很遗憾，{MAX_TRIES} 次机会已用完，答案是 {answer}。")
    return False, MAX_TRIES


def save_record(won, count):
    result = "胜" if won else "负"
    with open(SCORE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}|{result}|{count}\n")


def show_top5():
    try:
        with open(SCORE_FILE, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        lines = []
    wins = []
    for line in lines:
        parts = line.strip().split("|")
        if len(parts) == 3 and parts[1] == "胜" and parts[2].isdigit():
            wins.append((int(parts[2]), parts[0]))
    if not wins:
        print("还没有获胜记录，赢一局再来查看吧！")
        return
    print("—— 历史最少次数前 5 名（仅获胜局）——")
    for rank, (count, when) in enumerate(sorted(wins)[:5], 1):
        print(f"第 {rank} 名：{count} 次   {when}")


def main():
    while True:
        won, count = play_round()
        save_record(won, count)
        while True:
            choice = input("请选择：y=再来一局 s=查看排行榜 其他=退出：").strip().lower()
            if choice == "s":
                show_top5()
                continue
            break
        if choice != "y":
            print("感谢游玩，再见！")
            break


if __name__ == "__main__":
    main()

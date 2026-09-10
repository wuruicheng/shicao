import random

MAX_TRIES = 7


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
            return
    print(f"很遗憾，{MAX_TRIES} 次机会已用完，答案是 {answer}。")


def main():
    while True:
        play_round()
        again = input("再来一局吗？（输入 y 重开，其他输入退出）：").strip().lower()
        if again != "y":
            print("感谢游玩，再见！")
            break


if __name__ == "__main__":
    main()

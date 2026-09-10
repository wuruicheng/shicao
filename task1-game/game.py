import random


def main():
    answer = random.randint(1, 100)
    count = 0
    print("我想好了一个 1~100 的整数，请猜猜它是多少。")
    while True:
        text = input("请输入你的猜测：").strip()
        try:
            guess = int(text)
        except ValueError:
            print("这不是有效的整数，请重新输入。")
            continue
        count += 1
        if guess < answer:
            print("小了。")
        elif guess > answer:
            print("大了。")
        else:
            print(f"猜对了！你一共猜了 {count} 次。")
            break


if __name__ == "__main__":
    main()

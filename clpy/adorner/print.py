#!/bin/python3


def say_hello(contry):
    def wrapper(func):
        def echo(*args, **kwargs):
            if contry == "china":
                print("你好!")
            elif contry == "america":
                print("hello.")
            else:
                return

            func(*args, **kwargs)
        return echo
    return wrapper

@say_hello("china")
def american():
    print("我来自中国。")

@say_hello("america")
def chinese():
    print("I am from America.")


american()

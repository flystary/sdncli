#!/bin/python3


def logger(func):
    def wrapper(*args, **kw):
        print("111{}11".format(func.__name__))

        func(*args, **kw)

        print("22222")

    return wrapper

@logger
def add(x, y):
    print("{} + {} = {}".format(x, y, x+y))

add(200, 700)

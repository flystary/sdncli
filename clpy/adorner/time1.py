#!/bin/python3

import time


def timer(func):
    def wrapper(*args, **kw):
        t1 = time.time()
        func(*args, **kw)
        t2 = time.time()

        cost_time = t2 - t1
        print("花费时间: {}s".format(cost_time))

    return wrapper


@timer
def want_sleep(sleep_time):
    time.sleep(sleep_time)

want_sleep(10)


#!/bin/python3

import time
import timeit

def run_sleep(second):
    print(second)
    time.sleep(second)

# 只用这一行
print(timeit.timeit(lambda :run_sleep(2), number=1))

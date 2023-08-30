#!/bin/python3

from numba import jit
import time
import timeit

@jit
def foo(x,y):
    s = 0
    for i in range(x, y):
        s += i
    return s

foo(1, 100000000)
print(timeit.timeit(lambda :foo(1, 100000000), number=1))

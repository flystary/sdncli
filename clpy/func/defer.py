#!/bin/python3


import contextlib


def callback():
    print('B')

with contextlib.ExitStack() as stack:
    stack.callback(callback)
    print('A')

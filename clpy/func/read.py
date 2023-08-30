#!/bin/python3

from functools import partial



def read_from_file(filename, block_size = 1024 * 8):
    with open(filename, 'r') as fp:
        while True:
            chunk = fp.read(block_size)
            if not chunk:
                break

            yield chunk

def read_from_file(filename, block_size = 1024 * 8):
    with open(filename, 'r') as fp:
        for chunk in iter(partial(fp.read, block_size), ""):
            yield chunk


# python3.8
def read_from_file(filename, block_size = 1024 * 8):
    with open(filename, "r") as fp:
        while chunk := fp.read(block_size):
            yield chunk

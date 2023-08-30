#!/bin/python3


class Prod:
    def __init__(self, value):
        self.value = value

    def __call__(self, value):
        return self.value * value

p = Prod(2)
print(p(1))
print(p(2))
print(p(3))
print(p(4))
print(p(5))

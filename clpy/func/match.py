#!/bin/python3

def add(x):
    class AddInt(int):
        def __call__(self, x):
            return AddInt(self.numerator + x)
    return AddInt(x)


def mult(x):
    class MultInt(int):
        def __call__(self,x):
            return MultInt(self.numerator * x)
    return MultInt(x)


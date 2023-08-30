#!/bin/python3

"""
class logger(object):
    def __init__(self,func):
        self.func = func

    def __call__(self,*args,**kwargs):
        print("[INFO]: the function {func}() is runing..."\
              .format(func=self.func.__name__))
        return self.func(*args, **kwargs)

@logger
def say(something: str):
    print("say {}".format(something))


say("hello")
"""

class logger(object):
    def __init__(self, level='INFO'):
        self.level = level

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            print("[{level}]: the function {func}() is running..."\
                .format(level=self.level, func=func.__name__))
            func(*args, **kwargs)
        return wrapper

@logger(level="DEBUG")
def say(someting):
    print("say {}!".format(someting))

say("hello")

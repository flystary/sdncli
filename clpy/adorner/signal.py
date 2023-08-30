#!/bin/python


import signal
import time

class TimeoutException(Exception):
    def __init__(self, error="Timeout waiting for response from Cloud"):
        Exception.__init__(self, error)

def timeout_limit(timeout_time):
    def wraps(func):
        def handler(signum, frame):
            raise TimeoutException()

        def deco(*args, **kwargs):
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout_time)
            func(*args, **kwargs)
            signal.alarm(0)

        return deco

    return wraps

@timeout_limit(3)
def echo():
    time.sleep(2)


echo()

#!/bin/python3

import contextlib

@contextlib.contextmanager
def test_context(name):
    print('enter, my name is {}'.format(name))

    yield

    print('exit, my name is {}'.format(name))

with test_context('aaa'):
    with test_context('bbb'):
        print('========== in main ============')

print()
with test_context('aaa'), test_context('bbb'):
    print('========== in main ============')
    

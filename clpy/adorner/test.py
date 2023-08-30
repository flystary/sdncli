#!/bin/python3

class TestProperty(object):
    
    def __init__(self, fget=Nome,fset=None,fdel=None,doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.__doc__ = doc

    def __get__(self, obj, objtype=None):
        print("in __get__")
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError
        return self.fget(obj)

    def __set__(self, obj, value):
        print("in __set__")
        if self.fset is None:
            raise AttributeError
        self.fset(obj, value)

    def __delete__(self, obj):
        print("in __delete__")
        if self.fdel is None:
            raise AttributeError
        self.fdel(obj)


    def getter(self, fget):
        print("in getter")
        return type(self)(fget, self.fset, self.fdel, self.__doc__)

    def setter(self, fset):
        print("in setter")
        return type(self)(self.fget, fset, self.fdel, self.__doc__)

    def deleter(self, fdel):
        print("in deleter")
        return type(self)(self.fget, self.fset, fdel, self.__doc__)


class Student:
    def __init__(self, name):
        self.name = name

    @TestProperty
    def math(self):
        return self._math

    @math.setter
    def math(self, value):
        if 0 < value < 100:
            self._math = value
        else:
            raise ValueError("Valid value must be in (0, 100)")

"""
使用TestProperty装饰后，math 不再是一个函数，而是TestProperty 类的一个实例。所以第二个math函数可以使用 math.setter 来装饰，本质是调用TestProperty.setter 来产生一个新的 TestProperty 实例赋值给第二个math。
第一个 math 和第二个 math 是两个不同 TestProperty 实例。但他们都属于同一个描述符类（TestProperty），当对 math 对于赋值时，就会进入 TestProperty.__set__，当对math 进行取值里，就会进入 TestProperty.__get__。仔细一看，其实最终访问的还是Student实例的 _math 属性。
"""

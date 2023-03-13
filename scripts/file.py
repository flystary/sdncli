#!/bin/python3

import os
import json
#from svxutil.baseconf import *
from configparser import ConfigParser

class File(object):
    def __init__(self, path):
        self.path = path
        self.null = {}
        self.key  = ''
        self.value  = {}
        self.file = open(self.path, 'r', encoding='UTF-8')

        if self.path == "" and not isinstance(self.path, str):
            return self.null

    def get_key(self):
        if "/" in self.path:
            splits = self.path.split("/")
            if len(splits[-1]) == 0:
                self.key = splits[-2]
            else:
                self.key = splits[-1]
        else:
            self.key = splits
        return

    def is_conf(self):
        if '=' not in self.file.read():
            return False
        return True

    def is_json(self):
        try:
            obj = json.load(self.file)
        except ValueError:
            return False
        return True

    def conf_to_map(self):
        print(111)
        map = {}
        print(type(self.file))
        for line in self.file.readlines():
            key, value = line.strip().split('=')
            # 首字母为'#' 筛选掉
            if key.startswith("#") or len(value) == 0:
                continue
            map[key.strip()] = value.strip()
        # 关闭
        self.close()
        return map

    def json_to_map(self):
        obj = {}
        try:
            obj = json.load(self.file)
        except:
            return self.null
        # 关闭
        self.close()
        return obj

    def close(self):
        if self.file is None:
            return
        self.file.close()
        return

    def get_value(self):
        isconf = self.is_conf()
        isjson = self.is_json()

        print(isconf, isjson)
        if isconf:
            self.value = self.conf_to_map()

        if isjson:
            self.value = self.json_to_map()

        print(self.value)
        return

    def load(self):
        self.get_key()
        self.get_value()

    def dict(self):
        self.load()
        map = {}
        key   = self.key
        value = self.value

        if key == "" or value is None:
            return self.null
        map[key] = value

        return map

class Dir(object):
    pass

class Make(object):
    def init():
        pass


file = File("/usr/local/*/conf.d/glink/208/10423/update")
dict = file.dict()
print(dict)

#!/usr/bin/python3
#encoding:utf-8

import os
import sys
import json
import pickle
import getopt
import subprocess
from svxutil import *
from svxutil.baseconf import *

cmd_prefix = 'bgp'

# 获取命令参数
try:
    opts, args = getopt.getopt(sys.argv[1:], "f:", ["help", "file="],)
except getopt.GetoptError as e:
    print(e.msg)
    sys.exit(1)

for o, a in opts:
    if o in ("-f", "--file"):
        filename = a

# 加载json文件
try:
    dynamic_confs = json.load(open(filename))
except:
    sys.stderr.write("json文件加载失败!\n")
    sys.exit(1)

sync_file = '/usr/local/svxnetworks/conf.d/sync_dynamic_route.json'
pickle_path = "/usr/local/svxnetworks/conf.d/pickle"
dynamic_route_pkfile = '%s/dynamic_route.pk' % pickle_path

success = True
new_aspath = {}
new_prefixlist = {}
new_routemap = {}
dynamic_route = {}

try:
    # as-path
    asPaths     = dynamic_confs.get("asPaths", [])
    for index, asPath in enumerate(asPaths):
        try:
            name   = asPath.get("name").strip().lower()
            action = asPath.get("action").strip().lower()
            value  = asPath.get("actionValue").strip().lower()
        except:
            raise svxnetworksError('asPath %s 数据获取失败!' % index)

        if name not in new_aspath.keys():
            new_aspath[name]=set()
        new_aspath[name].add('%s %s' % (action, value))

    # 保存asPaths
    dynamic_route["asPaths"] = new_aspath

    # prefixlist
    prefixLists = dynamic_confs.get("prefixLists", [])
    for index, preFixList in enumerate(prefixLists):
        try:
            name   = preFixList.get("name").strip().lower()
            sequence = preFixList.get("seq", 0)
            action = preFixList.get("action").strip()
            cidr   = cidr_format(preFixList.get("cidr").strip().upper())
        except:
            raise svxnetworksError('prefixList %s 数据获取失败!' % index)

        if name not in new_prefixlist.keys():
            new_prefixlist[name]=set()
        new_prefixlist[name].add('seq %s %s %s' % (sequence, action, cidr))

    # 保存prefixLists
    dynamic_route["prefixLists"] = new_prefixlist

    # routemap
    routeMaps   = dynamic_confs.get("routeMaps", [])
    for index, routeMap in enumerate(routeMaps):
        try:
            name = routeMap.get("name").strip().lower()
            action = routeMap.get("action").strip().lower()
            sequence = routeMap.get("seq", 0)
            matchList = routeMap.get("matchList", [])
            setList   = routeMap.get("setList", [])
            matchPrefix = ""
            matchAsPath = ""
            localPreference = 0
            metric = 0
            asPathPrepend = ""

            if name == "" or action == "" or sequence <= 0:
                raise svxnetworksError('routeMap中 %s 的name或action或sequence错误!' % index)

            onlyNsdict = {}
            onlyNs = '%s|%s' % (name, sequence)
            onlyNsdict["name"] = name
            onlyNsdict["action"] = action
            onlyNsdict["sequence"] = sequence

            for match_dict in matchList:
                if match_dict.get("matchType", "") == "prefix-list":
                    matchPrefix = match_dict.get("matchValue", "").strip().lower()

                if match_dict.get("matchType", "") == "as-path":
                    matchAsPath = match_dict.get("matchValue", "").strip().lower()

            for set_dict in setList:
                if set_dict.get("setType", "") == "local-preference":
                    localPreference = int(set_dict.get("setValue", 0))

                if set_dict.get("setType", "") == "metric":
                    metric = int(set_dict.get("setValue", 0))

                if set_dict.get("setType", "") == "as-path-prepend":
                    asPathPrepend = set_dict.get("setValue", "").strip().lower()

            if matchAsPath != "":
                if matchAsPath not in new_aspath.keys():
                    raise svxnetworksError('asPath %s 在下发的asPaths中获取失败!' % index)
                onlyNsdict["matchAsPath"] = matchAsPath

            if matchPrefix != "":
                if matchPrefix not in new_prefixlist.keys():
                    raise svxnetworksError('prefixList %s 在下发的prefixLists中获取失败!' % index)
                onlyNsdict["matchPrefix"] = matchPrefix

            if onlyNs in new_routemap.keys():
                raise svxnetworksError('routeMap %s %s routeMaps中数据重复!' % (index, onlyNs))

            if localPreference > 0 :
                onlyNsdict["localPreference"] = localPreference
            if metric > 0:
                onlyNsdict["metric"] = metric
            if asPathPrepend != "":
                onlyNsdict["asPathPrepend"] = asPathPrepend

            new_routemap[onlyNs] = onlyNsdict
        except:
            raise svxnetworksError('routeMap %s 数据获取失败!' % index)
    # 保存routeMaps
    dynamic_route["routeMaps"] = new_routemap

except svxnetworksError as e:
    # print(e)
    success = False

except:
    sys.stderr.write('json解析错误')
    sys.exit(2)

# pickle目录
if not os.path.exists(pickle_path):
    os.makedirs(pickle_path)

# 加载原配置
old_aspath = {}
old_prefixlist = {}
old_routemap = {}
old_dynamic_confs = {}

if os.path.exists(dynamic_route_pkfile):
    try:
        old_dynamic_confs = pickle.load(open(dynamic_route_pkfile, 'rb'))
    except:
        sys.stderr.write("pickle文件加载失败!\n")
        sys.exit(3)

    try:
        old_aspath = old_dynamic_confs["asPaths"]
        old_prefixlist = old_dynamic_confs["prefixLists"]
        old_routemap = old_dynamic_confs["routeMaps"]
    except:
        sys.stderr.write('pickle解析错误')
        sys.exit(4)

if not success:
    sys.exit(2)

# print("new_aspath", new_aspath)
# print("new_prefixlist", new_prefixlist)
# print("new_routemap", new_routemap)
# print()

# print("old_aspath", old_aspath)
# print("old_prefixlist", old_prefixlist)
# print("old_routemap", old_routemap)
# print()

# 执行文件
vtyshcmd = '/tmp/vtysh_dynamic_route.cmd'
vtysh_fp = open(vtyshcmd, 'w')
vtysh_fp.write('configure terminal\n')

# aspath
for asname in new_aspath.keys():
    if asname in old_aspath.keys():
        old_asvalue_list = old_aspath[asname]
    else:
        old_asvalue_list = set()

    for asvalue in (new_aspath[asname] - old_asvalue_list):
        vtysh_fp.write('%s as-path access-list %s %s\n' % (cmd_prefix, asname, asvalue))

    for old_asvalue in (old_asvalue_list - new_aspath[asname]):
        vtysh_fp.write('no %s as-path access-list %s %s\n' % (cmd_prefix, asname, old_asvalue))

for asname in old_aspath.keys():
    if asname not in new_aspath.keys():
        vtysh_fp.write('no %s as-path access-list %s \n' %(cmd_prefix, asname))

# prefixlist
for pflname in new_prefixlist.keys():
    if pflname in old_prefixlist.keys():
        old_pflvalue_list = old_prefixlist[pflname]
    else:
        old_pflvalue_list = set()

    for pflvalue in (new_prefixlist[pflname] - old_pflvalue_list):
        vtysh_fp.write("ip prefix-list %s %s\n" % (pflname, pflvalue))

    for old_pflvalue in (old_pflvalue_list - new_prefixlist[pflname]):
        vtysh_fp.write('no ip prefix-list %s %s\n' % (pflname, old_pflvalue))

for pflname in old_prefixlist.keys():
    if pflname not in new_prefixlist.keys():
        vtysh_fp.write('no ip prefix-list %s \n' % pflname)

# routemap
del_routemaps  = set()
same_routemaps = set()
add_routemaps  = set(new_routemap.keys()) - set(old_routemap.keys())

for onlyns in old_routemap.keys():
    if onlyns not in new_routemap.keys():
        del_routemaps.add(onlyns)
    else:
        same_routemaps.add(onlyns)

# 删除云端已删除的routemap
for onlyns in del_routemaps:
    value_dict =  old_routemap[onlyns]
    name        = value_dict.get("name", "")
    action      = value_dict.get("action", "")
    sequence    = value_dict.get("sequence", 0)

    if name == "" or action == "" or sequence <= 0:
        continue

    vtysh_fp.write("no route-map %s %s %s\n" % (name, action, sequence))

# 对比
for onlyns in same_routemaps:
    value_dict =  new_routemap[onlyns]
    name        = value_dict.get("name", "")
    action      = value_dict.get("action", "")
    sequence    = value_dict.get("sequence", 0)
    matchAsPath = value_dict.get("matchAsPath", "")
    matchPrefix = value_dict.get("matchPrefix", "")
    localPreference = int(value_dict.get("localPreference", 0))
    metric      = int(value_dict.get("metric", 0))
    asPathPrepend   = value_dict.get("asPathPrepend", "")

    if name == "" or action == "" or sequence <= 0:
        continue

    vtysh_fp.write("route-map %s %s %s\n" % (name, action, sequence))

    if matchAsPath == "":
        vtysh_fp.write("no match as-path\n")
    else:
        vtysh_fp.write("match as-path %s\n" %  matchAsPath)

    if matchPrefix == "":
        vtysh_fp.write("no match ip address prefix-list\n")
    else:
        vtysh_fp.write("match ip address prefix-list %s\n" % matchPrefix)

    if localPreference > 0:
        vtysh_fp.write("set local-preference %s\n" % localPreference)
    else:
        vtysh_fp.write("no set local-preference\n")

    if metric > 0:
        vtysh_fp.write("set metric %s\n" % metric)
    else:
        vtysh_fp.write("no set metric\n")

    if asPathPrepend == "":
        vtysh_fp.write("no set as-path prepend\n")
    else:
        vtysh_fp.write("set as-path prepend %s\n" % asPathPrepend)

# 新增
for onlyns in add_routemaps:
    value_dict =  new_routemap[onlyns]
    name        = value_dict.get("name", "")
    action      = value_dict.get("action", "")
    sequence    = value_dict.get("sequence", 0)
    matchAsPath = value_dict.get("matchAsPath", "")
    matchPrefix = value_dict.get("matchPrefix", "")
    localPreference = value_dict.get("localPreference", 0)
    metric      = int(value_dict.get("metric", 0))
    asPathPrepend   = value_dict.get("asPathPrepend", "")

    if name == "" or action == "" or sequence <= 0:
        continue

    vtysh_fp.write("route-map %s %s %s\n" % (name, action, sequence))

    if matchAsPath != "":
        vtysh_fp.write("match as-path %s\n" %  matchAsPath)
    if matchPrefix != "":
        vtysh_fp.write("match ip address prefix-list %s\n" % matchPrefix)
    if localPreference > 0:
        vtysh_fp.write("set local-preference %s\n" % localPreference)
    if metric > 0:
        vtysh_fp.write("set metric %s\n" % metric)
    if asPathPrepend != "":
        vtysh_fp.write("set as-path prepend %s\n" % asPathPrepend)

vtysh_fp.write('end\n')
vtysh_fp.write('clear ip bgp * soft\n')
vtysh_fp.write('write\n')
vtysh_fp.write('quit\n')
vtysh_fp.flush()
vtysh_fp.close()

status, result = subprocess.getstatusoutput('vtysh < %s' % vtyshcmd)
if 'locked by' in result:
    sys.exit(9)
if 'Command incomplete' in result:
    sys.exit(9)
if 'Unknown command' in result:
    sys.exit(9)
if 'failed'in result:
    sys.exit(9)

# 保存最新的dynamic_route_pkfile
with open(dynamic_route_pkfile, "wb") as file_to_write:
    pickle.dump(dynamic_route, file_to_write)

os.rename(filename, sync_file)
sys.exit(0)

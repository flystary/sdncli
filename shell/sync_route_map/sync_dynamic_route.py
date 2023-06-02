#!/usr/bin/python3
#encoding:utf-8

import os
import sys
import json
import getopt
import subprocess
from svxutil import *
from svxutil.baseconf import *

cmd_prefix = 'bgp'
global_prefix = 'global-'

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
success = True

new_aspath = {}
new_prefixlist = {}
new_routemap = {}

try:
    # as-path
    asPaths     = dynamic_confs.get("asPaths", [])
    if not asPaths:
        success = False
        raise svxnetworksError('asPaths为空!')

    for index, asPath in enumerate(asPaths):
        try:
            name = '%s%s' % (global_prefix, asPath.get("name").strip().lower())
            action = asPath.get("action", 'permit').strip().lower()
            value  = asPath.get("actionValue").strip().lower()
        except:
            raise svxnetworksError('asPath %s 数据获取失败!' % index)

        if name not in new_aspath.keys():
            new_aspath[name]=set()
        new_aspath[name].add('%s %s' % (action, value))

    # prefixlist
    prefixLists = dynamic_confs.get("prefixLists", [])
    if not prefixLists:
        success = False
        raise svxnetworksError('prefixLists为空!')

    for index, preFixList in enumerate(prefixLists):
        try:
            name   = '%s%s' % (global_prefix, preFixList.get("name").strip().lower())
            sequence = preFixList.get("seq", 0)
            action = preFixList.get("action").strip()
            cidr   = cidr_format(preFixList.get("cidr").strip().upper())
        except:
            raise svxnetworksError('prefixList %s 数据获取失败!' % index)

        if name not in new_prefixlist.keys():
            new_prefixlist[name]=set()
        new_prefixlist[name].add('seq %s %s %s' % (sequence, action, cidr))

    # routemap
    routeMaps   = dynamic_confs.get("routeMaps", [])
    if not routeMaps:
        success = False
        raise svxnetworksError('routeMaps为空!')

    for index, routeMap in enumerate(routeMaps):
        try:
            tname = routeMap.get("name").strip().lower()
            name = '%s%s' % (global_prefix, tname)
            sequence = routeMap.get("seq", 0)
            matchList = routeMap.get("matchList", [])
            setList   = routeMap.get("setList", [])
            matchPrefix = ""
            matchAsPath = ""
            localPreference = 0
            metric = 0
            asPathPrepend = ""

            for math_dict in matchList:
                if math_dict.get("matchType", "") == "prefix-list":
                    matchPrefix = math_dict.get("matchValue", "").strip().lower()

                if math_dict.get("matchType", "") == "as-path":
                    matchAsPath = math_dict.get("matchValue", "").strip().lower()

            for set_dict in setList:
                if set_dict.get("setType", "") == "local-preference":
                    localPreference = set_dict.get("setValue", 0)

                if set_dict.get("setType", "") == "metric":
                    metric = set_dict.get("setValue", 0)

                if set_dict.get("setType", "") == "as-path-prepend":
                    asPathPrepend = set_dict.get("setValue", "").strip().lower()

            GmatchAsPath = '%s%s' % (global_prefix, matchAsPath)
            GmatchPrefix = '%s%s' % (global_prefix, matchPrefix)

            if GmatchAsPath not in new_aspath.keys():
                raise svxnetworksError('asPath %s 在下发的asPaths中获取失败!' % index)

            if GmatchPrefix not in new_prefixlist.keys():
                raise svxnetworksError('prefixList %s 在下发的prefixLists中获取失败!' % index)

            onlyNs = '%s|%s' % (name, sequence)
            onlyNsdict = {}

            if onlyNs in new_routemap.keys():
                raise svxnetworksError('routeMap %s %s routeMaps中数据重复!' % (index, onlyNs))

            if name != "" and name != global_prefix:
                onlyNsdict["name"] = name
            if sequence > 0:
                onlyNsdict["sequence"] = sequence
            if matchAsPath != "":
                onlyNsdict["matchAsPath"] = GmatchAsPath
            if matchPrefix != "":
                onlyNsdict["matchPrefix"] = GmatchPrefix
            if localPreference > 0 :
                onlyNsdict["localPreference"] = localPreference
            if metric > 0:
                onlyNsdict["metric"] = metric
            if asPathPrepend != "":
                onlyNsdict["asPathPrepend"] = asPathPrepend

            new_routemap[onlyNs] = onlyNsdict

        except:
            raise svxnetworksError('routeMap %s 数据获取失败!' % index)

except svxnetworksError as e:
    success = False

except Exception as e:
    sys.stderr.write('json解析错误')
    sys.exit(1)

# 加载原配置
old_aspath = {}
old_prefixlist = {}
old_routemap = {}

with open(bgpd_conf) as f:
    for index, line in enumerate(f):
        # asPath
        if line.startswith('%s as-path access-list %s' % (cmd_prefix, global_prefix)):
            tmp = line.strip().split()
            if len(tmp) < 6:
                continue

            if "seq" in tmp:
                asname = tmp[3]
                action = tmp[6]
                value = ' '.join(tmp[7:])
            else:
                asname, action = tmp[3:5]
                value = ' '.join(tmp[5:])

            if asname not in old_aspath.keys():
                old_aspath[asname]=set()
            old_aspath[asname].add('%s %s' % (action, value))

        # prefixList
        if line.startswith('ip prefix-list %s' % global_prefix):
            tmp = line.strip().split()
            if len(tmp) < 7:
                continue
            pflname = tmp[2]
            sequence = tmp[4]
            action = tmp[5]
            cidr   = tmp[6]
            if pflname not in old_prefixlist.keys():
                old_prefixlist[pflname] = set()
            old_prefixlist[pflname].add("seq %s %s %s" % (sequence, action, cidr))

    # routemap
    f.seek(0)
    pieces = f.read().split("!")
    for piece in pieces:
        if "route-map" in piece and global_prefix in piece:
            onlyNsdict={}
            action = ""
            sequence = 0
            matchAsPath = ""
            matchPrefix = ""
            localPreference = 0
            metric = 0
            asPathPrepend =""
            for line in piece.strip().splitlines():

                tmp = line.split()
                # route-map
                if tmp[0] == "route-map" and tmp[1].startswith(global_prefix) and tmp[2] == "permit":
                    name=tmp[1]
                    sequence=tmp[3]
                # match
                if tmp[0] == "match":
                    if tmp[1] == "as-path":
                        matchAsPath=tmp[2]
                    if tmp[1] == "ip" and tmp[2]=="address" and tmp[3]=="prefix-list":
                        matchPrefix=tmp[4]
                # set
                if tmp[0] == "set":
                    if tmp[1] == "metric":
                       metric=tmp[2]
                    if tmp[1] == "local-preference":
                       localPreference=tmp[2]
                    if tmp[1] == "as-path" and tmp[2]=="prepend":
                       asPathPrepend  = ' '.join(tmp[3:])

                onlyNs = '%s|%s' % (name, sequence)
                if onlyNs in old_routemap.keys():
                    sys.stderr.write('OldrouteMap %s %s 数据重复!' % (index, onlyNs))

                if name != "":
                    onlyNsdict["name"] = name
                if int(sequence) > 0:
                    onlyNsdict["sequence"] = int(sequence)
                if matchAsPath != "":
                    onlyNsdict["matchAsPath"] = matchAsPath
                if matchPrefix != "":
                    onlyNsdict["matchPrefix"] = matchPrefix

                if int(localPreference) > 0 :
                    onlyNsdict["localPreference"] = int(localPreference)
                if int(metric) > 0:
                    onlyNsdict["metric"] = int(metric)
                if asPathPrepend != "":
                    onlyNsdict["asPathPrepend"] = asPathPrepend

            if onlyNs not in old_routemap.keys():
                old_routemap[onlyNs] = {}
            old_routemap[onlyNs] = onlyNsdict

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
vtyshcmd = '/tmp/dynamic_route_tmp'
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
    sequence    = value_dict.get("sequence", 0)

    if name == "" or sequence <= 0:
        continue

    vtysh_fp.write("no route-map %s permit %s\n" % (name, sequence))

# 对比
for onlyns in same_routemaps:
    value_dict =  new_routemap[onlyns]
    name        = value_dict.get("name", "")
    sequence    = value_dict.get("sequence", 0)
    matchAsPath = value_dict.get("matchAsPath", "")
    matchPrefix = value_dict.get("matchPrefix", "")
    localPreference = value_dict.get("localPreference", 0)
    metric      = value_dict.get("metric", 0)
    asPathPrepend   = value_dict.get("asPathPrepend", "")

    if name == "" or sequence <= 0:
        continue

    vtysh_fp.write("route-map %s permit %s\n" % (name, sequence))

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
    sequence    = value_dict.get("sequence", 0)
    matchAsPath = value_dict.get("matchAsPath", "")
    matchPrefix = value_dict.get("matchPrefix", "")
    localPreference = value_dict.get("localPreference", 0)
    metric      = value_dict.get("metric", 0)
    asPathPrepend   = value_dict.get("asPathPrepend", "")

    if name == "" or sequence <= 0:
        continue

    vtysh_fp.write("route-map %s permit %s\n" % (name, sequence))

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
    sys.exit(2)
if 'Command incomplete' in result:
    sys.exit(2)
if 'Unknown command' in result:
    sys.exit(2)
if 'failed'in result:
    sys.exit(2)

os.rename(filename, sync_file)
sys.exit(0)

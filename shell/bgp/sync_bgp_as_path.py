#!/usr/bin/python3
#encoding:utf-8

import os
import sys
import json
import getopt
import subprocess
from svxutil.baseconf import *

cmd_prefix = 'bgp'
aspath_prefix = 'global-'

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
    aspath_confs = json.load(open(filename))
except:
    sys.stderr.write("json文件加载失败!\n")
    sys.exit(1)

old_aspath = {}

# 加载原aspath配置
with open(bgpd_conf) as f:
    for line in f:
        if line.startswith('%s as-path access-list %s' % (cmd_prefix, aspath_prefix)):
            tmp = line.strip().split()
            if len(tmp) < 6:
                continue
            name, action = tmp[3:5]
            value = ' '.join(tmp[5:])
            if name not in old_aspath.keys():
                old_aspath[name]=set()

            old_aspath[name].add('%s %s' % (action, value))

sync_file = '/usr/local/svxnetworks/conf.d/sync_bgp_aspath.json'

aspath={}

for rule_dict in aspath_confs:
    try:
        name = '%s%s' % (aspath_prefix, rule_dict.get("name").strip().lower())
        action = rule_dict.get("action", 'permit').strip().lower()
        value  = rule_dict.get("actionValue").strip().lower()
    except:
        sys.exit(2)

    if name not in aspath.keys():
        aspath[name]=set()

    aspath[name].add('%s %s' % (action, value))

vtysh_cmd = '/tmp/network_aspath'
vtysh_fp = open(vtysh_cmd, 'w')
vtysh_fp.write('configure terminal\n')

for name in aspath.keys():
    if name in old_aspath.keys():
        old_av_list = old_aspath[name]
    else:
        old_av_list = set()

    for av in aspath[name] - old_av_list:
        vtysh_fp.write('%s as-path access-list %s %s\n' % (cmd_prefix, name, av))

    for old_av in old_av_list - aspath[name]:
        vtysh_fp.write('no %s as-path access-list %s %s\n' % (cmd_prefix, name, old_av))

for name in old_aspath.keys():
    if name not in aspath.keys():
        vtysh_fp.write('no %s as-path access-list %s \n' %(cmd_prefix, name))

vtysh_fp.write('end\n')
vtysh_fp.write('clear ip bgp * soft\n')
vtysh_fp.write('write\n')
vtysh_fp.write('quit\n')
vtysh_fp.flush()
vtysh_fp.close()

status, result = subprocess.getstatusoutput('vtysh < %s' % vtysh_cmd)
if 'locked by' in result:
    sys.exit(2)
if 'Command incomplete' in result:
    sys.exit(2)
if 'Unknown command' in result:
    sys.exit(2)
if 'failed'in result:
    sys.exit(2)

#os.rename(filename, sync_file)
sys.exit(0)

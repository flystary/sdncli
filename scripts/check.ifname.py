#!/usr/bin/python3
# encoding:utf-8
import os
import re
import sys


def get_name(path, name):
    name_list = []
    file = os.listdir(path)
    for i in file:
        if name == 'vlan':
            # nm = ("%s\d+" % name)
            s =re.findall(re.compile(("%s\d+" % name)), i)
            [name_list.append(j) for j in s]
        elif name == "tunnel" or name == "glink":
            name_list.append(i)
        elif name == "gre":
            with open('%s%s' % (path, i), 'r') as grepf:
                for line in grepf.readlines():
                    k, v = line.strip().split('=')
                    if k == "gre_name":
                        name_list.append(v.rstrip())
                    else:
                        continue
            grepf.close()
            #name_list.append(i.rstrip('.sh'))
        else:
            print("网络类型错误")
            sys.exit(1)

    return name_list


# ppp
ppp = ['ppp11=WAN1', 'ppp12=WAN2']

# network
network = []
with open('/etc/*/conf.d/network.conf','r') as fp:
    n_list = fp.readlines()
fp.close()

for line in n_list:
    name, interface = line.strip().split('=')
    if name == "MOBILE4G":
        name = "MOBILE-4G"
    elif name == "MOBILE5G":
        name = "MOBILE-5G"
    # elif name == "WIFI_IFNAME":
    #     name = "WLAN0"

    if os.path.exists("/sys/class/net/%s" % interface):
        line_format = '%s=%s' % (interface, name)
        network.append(line_format)

# bond
bond = []
for b in ["bond0","bond1"]:
    bondUpper = b.upper()
    if os.path.exists("/sys/class/net/%s" % b):
        line_format = '%s=%s' % (b, bondUpper)
        bond.append(line_format)

# vlan
vlan = []
vlan_path = "/sys/class/net/"
name="vlan"
for v in  get_name(vlan_path,name):
    vlan.append('%s=%s' % (v,v.upper()))

# gre
gre = []
path = "/usr/local/*/conf.d/gretunnel/"
name = "gre"
if os.path.exists(path):
    for e in get_name(path, name):
        gre.append('%s=%s' % (e, e))

# tunnel
tunnel = []
path = "/usr/local/*/conf.d/tunnel/"
name = "tunnel"
if os.path.exists(path):
   for t in  get_name(path, name):
       t1 = 'ipip%s' % (t)
       t2 = 'INTERCONNECTION-%s' %(t)
       tunnel.append('%si=%s' % (t1, t2))
       tunnel.append('%ss=%s' % (t1, t2))

# glink
glink = []
path = "/usr/local/*/conf.d/glink/"
name = "glink"
if os.path.exists(path):
    for g in  get_name(path,name):
        g1 = 'glink%s'  % (g)
        g2 = 'GLINK-%s' % (g)
        glink.append('%s=%s' % (g1, g2))


# 写入配置文件
ifpath = "/usr/local/*/conf.d/ifname.conf"

if not os.path.exists("/usr/local/*/conf.d/"):
    os.makedirs("/usr/local/*/conf.d/")

if_name = []
for x in (ppp, network, bond, vlan, gre):
    if_name.extend(x)

# 互联加起来超过10,互联不上报
tunnel_len = len(tunnel) / 2
glink_len  = len(glink)

if tunnel_len + glink_len < 10 :
    for x in (tunnel, glink):
        if_name.extend(x)

with open(ifpath, "w") as ifconf:
    for conf in if_name:
        ifconf.write(conf + '\n')
ifconf.close()

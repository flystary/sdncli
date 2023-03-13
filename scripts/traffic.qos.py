#!/usr/bin/python3

import os
import re
import sys
import json
import subprocess

qos_root     = "/usr/local/*/conf.d/qos"
glink_root   = "/usr/local/*/conf.d/glink"
tunnel_root  = "/usr/local/*/conf.d/tunnel"
network_conf = "/etc/*/conf.d/network.conf"
qos_run_root = '/var/run/*/qos'

def get_qos_class_info():
    qos_class_mapping = {}
    cmd = "ls %s/class*.conf" % qos_root
    status, result = subprocess.getstatusoutput(cmd)
    if status != 0:
        return {}

    res = re.split(r'\n', result)
    for file in res:
        class_id, class_type = get_class_id_type_by_file(file)
        qos_class_mapping[class_id] = class_type

    return qos_class_mapping

def get_class_id_type_by_file(qosfile):
    class_id   = 0
    class_type = 0
    if os.path.exists(qosfile):
        try:
            conf = qosfile.split("/")[-1]
            class_id = re.sub(r'\D', '', conf)
        except:
            pass

        abys = open(qosfile, 'r', encoding='UTF-8')
        try:
            for line in abys.readlines():
                key, value = line.strip().split('=')
                if key.startswith("#"):
                    continue
                if key.strip() == "class_type_conf":
                    class_type = value.strip()
                    break
        finally:
            abys.close()

    return class_id, class_type

def get_qos_tmps_by_interface(interface):
    cmd = "tc -s class show dev %s" % interface
    print(cmd)
    status, result = subprocess.getstatusoutput(cmd)
    if status != 0:
        return ''

    return result

def get_id_and_tx_dict(result):
    res = re.split(r'\n\n', result)
    tx_dict = {}
    for piece in res:
        traffic_tx = 0
        cls = ""

        for line in piece.splitlines():
            tmp = line.split()
            if 'class' in line:
                cls = tmp[2]
            if 'Sent' in line:
                traffic_tx = tmp[1]
        if len(cls) == 0 and traffic_tx == 0:
            continue
        tx_dict[cls] = traffic_tx

    # 删除1:1 1:255
    if '1:1' in tx_dict:
        tx_dict.pop("1:1")
    #if '1:10' in tx_dict:
    #    tx_dict.pop("1:10")
    if '1:255' in tx_dict:
        tx_dict.pop("1:255")

    return tx_dict

def get_tunnel_interfaces_by_file():
    interfaces = set()
    for dir in os.listdir(tunnel_root):
        try:
            id = int(dir)
            if id > 0 :
                tunnels = 'ipip%ds' % id
                tunneli = 'ipip%di' % id

                interfaces.add(tunnels)
                interfaces.add(tunneli)
        except:
            continue

    return interfaces

def get_gilnk_interfaces_by_file():
    interfaces = set()
    for dir in os.listdir(glink_root):
        try:
            id = int(dir)
            if id > 0 :
                glink = 'glink%s' % id
                interfaces.add(glink)
        except:
            continue
    return interfaces

def get_network_interfaces_by_file():
    interface_dict = {}
    if os.path.exists(network_conf):
        abys = open(network_conf, 'r', encoding='UTF-8')
        try:
            for line in abys.readlines():
                key, value = line.strip().split('=')
                if key.startswith("#"):
                    continue
                interface_dict[key.strip()] = value.strip()
        finally:
            abys.close()
    return interface_dict


def get_interfaces_by_class_type(class_type):
    interfaces = set()
    if class_type == "wan":
        netwrk_dict = get_network_interfaces_by_file()
        for wan in ['WAN1', 'WAN2','MOBILE4G', 'MOBILE5G']:
            interface = netwrk_dict.get(wan, "")
            if interface == "":
                continue
            interfaces.add(interface)
    elif class_type == "interconnection":
        tunnels = get_tunnel_interfaces_by_file()
        glinks  = get_gilnk_interfaces_by_file()
        # 并集
        interfaces = tunnels|glinks
        #interfaces = interfaces.union(tunnels, glinks)

    elif class_type.startswith("lan"):
        netwrk_dict = get_network_interfaces_by_file()
        interface = netwrk_dict.get(class_type.upper(), "")
        if interface != "":
            interfaces.add(interface)
    elif class_type.startswith("vlan"):
        interfaces.add(class_type)
    else:
        pass

    return interfaces

# qos配置文件
qos_dict = get_qos_class_info()
'''
{'11': 'wan', '12': 'lan1', 13:'vlan7', 14:'interconnection'}
'''
if len(qos_dict) == 0:
    sys.exit(0)

if not os.path.exists(qos_run_root):
    os.makedirs(qos_run_root)

for id, class_type in qos_dict.items():
    class_id = '1:%s' % id
    interfaces = get_interfaces_by_class_type(class_type)
    '''
    vlan7 {'vlan7'}
    lan2  {'fm1-mac6'}
    wan   {'usb4g', 'fm1-mac1', 'usb5g', 'fm1-mac2'}
    interconnection {'glink10004', 'ipip10003s', 'ipip10003i'}
    '''
    stx = 0
    for interface in interfaces:
        result = get_qos_tmps_by_interface(interface)
        tx_dict = get_id_and_tx_dict(result)
        '''
        {}
        {'1:13': '0'}
        {'1:10': '1017032', '1:12': '0'}
        '''
        tx = tx_dict.get(class_id, 0)
        stx = int(tx) + stx

    # write file
    class_run_file  = "%s/%s" % (qos_run_root, id)
    class_run_file1 = "%s/%s.1" % (qos_run_root, id)

    if os.path.exists(class_run_file):
        os.rename(class_run_file, class_run_file1)

    with open(class_run_file, 'w') as f:
        f.write('%s\n' % stx)

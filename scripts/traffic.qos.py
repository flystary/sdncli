#!/usr/bin/python3

import os
import re
import sys
import time
import sched
import shutil
import subprocess

qos_root     = "/usr/local/*/conf.d/qos"
glink_root   = "/usr/local/*/conf.d/glink"
tunnel_root  = "/usr/local/*/conf.d/tunnel"
network_conf = "/etc/*/conf.d/network.conf"
qos_run_root = '/var/run/*/qos'

def get_qos_class_info():
    qos_class_mapping = {}
    if os.path.exists(qos_root):
        cmd = "ls %s/class*.conf" % qos_root
        status, tmp = subprocess.getstatusoutput(cmd)
        if status != 0:
            return {}

        res = re.split(r'\n', tmp)
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

def get_qos_tmps_by_interface(dev):
    tmp_result = ""
    cmd = "/usr/sbin/tc -s class show dev %s" % dev
    try:
        tmp_result = subprocess.getoutput(cmd)
    except:
        pass

    return tmp_result

def get_id_and_tx_dict(tmp):
    res = re.split(r'\n\n', tmp)
    tx_dict = {}
    for piece in res:
        tx  = int(0)
        cls = ""

        for line in piece.splitlines():
            tmp = line.split()
            if tmp[0] == "class" and tmp[1] == "htb" and tmp[3] == "parent":
                cls = tmp[2]
            elif tmp[0] == "Sent" and tmp[2] == "bytes":
                tx = int(tmp[1])
            else:
                continue

        if len(cls) == 0:
            continue

        tx_dict[cls] = tx

    # 删除1:1 1:255 1:10
    if "1:1" in tx_dict:
        tx_dict.pop("1:1")
    if "1:10" in tx_dict:
        tx_dict.pop("1:10")
    if "1:255" in tx_dict:
        tx_dict.pop("1:255")

    return tx_dict

def get_tunnel_interfaces_by_file():
    interfaces = set()
    if os.path.exists(tunnel_root):
        for dir in os.listdir(tunnel_root):
            try:
                id = int(dir)
                if id > 0 :
                    tunnels = "ipip%ds" % id
                    tunneli = "ipip%di" % id

                    interfaces.add(tunnels)
                    interfaces.add(tunneli)
            except:
                continue

    return interfaces

def get_gilnk_interfaces_by_file():
    interfaces = set()
    if os.path.exists(glink_root):
        for dir in os.listdir(glink_root):
            try:
                id = int(dir)
                if id > 0 :
                    glink = "glink%s" % id
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
        for wan in ["WAN1", "WAN2","MOBILE4G", "MOBILE5G"]:
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

# def do():
# qos配置文件
qos_dict = get_qos_class_info()
'''
{'11': 'wan', '12': 'lan1', 13:'vlan7', 14:'interconnection'}
'''
if len(qos_dict) == 0:
    sys.exit(0)

if not os.path.exists(qos_run_root):
    os.makedirs(qos_run_root)

ret = {}
for id, class_type in qos_dict.items():
    class_id = "1:%s" % id
    interfaces = get_interfaces_by_class_type(class_type)

    if len(interfaces) == 0:
        continue
    '''
    vlan7 {'vlan7'}
    lan2  {'fm1-mac6'}
    wan   {'usb4g', 'fm1-mac1', 'usb5g', 'fm1-mac2'}
    interconnection {'glink10004', 'ipip10003s', 'ipip10003i'}
    '''

    sum_tx = int(0)
    results = []
    for interface in interfaces:
        if interface in ret.keys():
            result = ret[interface]
        else:
            result = get_qos_tmps_by_interface(interface)
            ret[interface] = result

        results.append(result)
        tx_dict = get_id_and_tx_dict(result)
        '''
        {}
        {'1:13': '0'}
        {'1:10': '1017032', '1:12': '0'}
        '''
        tx = tx_dict.get(class_id, 0)
        sum_tx = sum_tx + tx
    #
    class_run_file  = "%s/%s" % (qos_run_root, id)
    class_run_file_tmp = "%s/%s.tmp" % (qos_run_root, id)
    class_run_file_old = "%s/%s.1" % (qos_run_root, id)
    class_run_file_old_tmp = "%s/%s.1.tmp" % (qos_run_root, id)

    if os.path.exists(class_run_file_tmp):
        shutil.copy(class_run_file_tmp, class_run_file_old_tmp)

    with open(class_run_file_tmp, 'w') as fw:
        for res in results:
            fw.write("%s\n" % res)

    if os.path.exists(class_run_file):
        shutil.copy(class_run_file, class_run_file_old)
        # try:
        #     subprocess.check_call("/bin/cp %s  %s" % (class_run_file, class_run_file_old))
        # except:
        #     pass

    with open(class_run_file, 'w') as f:
        f.write("%s\n" % sum_tx)

def crontab():
    cron.enter(60, 0, crontab, ())
    do()

cron = sched.scheduler(time.time, time.sleep)
# # 第一次任务，马上执行
cron.enter(0, 0, crontab, ())
cron.run()

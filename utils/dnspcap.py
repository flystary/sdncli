#!/usr/bin/python3
import os
import sys
import signal
import json
import pcap
import struct
import socket
import subprocess
# from multiprocessing import Process, Queue
from threading import Thread,Lock
from queue import Queue
import logging
from logging.handlers import TimedRotatingFileHandler

collection_cfg = '/usr/local/xx/conf.d/collections.domain.json'
domain_snat_rule_file = '/usr/local/xx/conf.d/sync_domain_snat.json'
acl_rule_file = '/usr/local/xx/conf.d/sync_security_rule.json'

def get_domain_snat_id():
    # 从sync_domain_snat.json加载再使用的集合
    used_ids = set()
    if os.path.exists(domain_snat_rule_file):
        try:
            snat_rules = json.load(open(domain_snat_rule_file))
        except:
            pass

        for snat_rule in snat_rules:
            try:
                used_id = snat_rule.get("dstDomainsId", 0)
                if used_id > 0:
                    used_ids.add(used_id)
            except:
                continue
    return used_ids

def get_acl_id():
# 从acl的配置文件里读取
    used_ids = set()
    if os.path.exists(acl_rule_file):
        try:
            acl_rules = json.load(open(acl_rule_file))
        except:
            pass

        for acl_rule in acl_rules:
            try:
                used_id = acl_rule.get("dstDomainCollectionId", 0)
                if used_id > 0:
                    used_ids.add(used_id)
            except:
                continue
    return used_ids

def get_collection_cfg(used_ids):
    '''
    返回字典格式，示例：
    cfg = {
        "www.baidu.com": {"collection":[1], "iplist":[]},
        "163.com": {"collection":[1, 2], "iplist":[]}
    }
    '''
    cfg = {}
    if os.path.exists(collection_cfg):
        for collection in json.load(open(collection_cfg)):

            collection_id = collection["id"]
            # 没使用的集合，不加载
            if collection_id not in used_ids:
                continue
            item_list = collection["snatDomainCollectionItemList"]
            if not isinstance(item_list, list):
                continue

            for d in item_list:
                domain = d["domain"]
                if domain in cfg.keys():
                    cfg[domain]["collection"].append(collection_id)
                else:
                    cfg[domain] = {"collection": [collection_id], "iplist":[]}
    return cfg


def ip_str_to_int(ip_str):
    # ip 点分十进制格式转int格式
    return struct.unpack("!I",socket.inet_aton(ip_str))[0]

def ip_int_to_str(ip_int):
    # ip int格式转点分十进制格式
    return socket.inet_ntoa(struct.pack("I", socket.htonl(ip_int)))

def ip_split_to_str(ip_split):
    # 长度为4的int列表转点分十进制格式
    return '.'.join([str(i) for i in ip_split])

def check_ipset():
    collection_id_list = []
    for key, value in domain_collections.items():
        l = value["collection"]
        if isinstance(l, list):
            collection_id_list.extend(l)
    for collection_id in set(collection_id_list):
        try:
            subprocess.check_call('ipset -q -n list snatdomain%s' % collection_id, shell=True)
        except:
            try:
                subprocess.check_call('ipset -q -N --exist snatdomain%s hash:ip' % collection_id, shell=True)
            except:
                pass


def add_ipset(collection_id, ip_int):
    # ip_str = ip_int_to_str(ip_int)
    # shell_cmd = 'ipset -q --exist add snatdomain%s %s' % (collection_id, ip_str)
    # ipset可以直接使用int格式的ip地址
    shell_cmd = 'ipset -q --exist add snatdomain%s %s' % (collection_id, ip_int)
    try:
        subprocess.check_call(shell_cmd, shell=True)
    except:
        pass

def check_or_add_ipset(domain, ip_int):
    for key, value in domain_collections.items():
        # 如果域名没匹配中，继续匹配下一个
        if not domain.endswith(key):
            continue
        # 这个域名对应的ip已经添加过，不需要添加
        if ip_int in value["iplist"]:
            continue
        # 这个域名对应的所有集合都需要添加
        for collection_id in value["collection"]:
            add_ipset(collection_id, ip_int)
            value["iplist"].append(ip_int)
            logger.info("%s:match %s, add %s to ipset snatdomain%s" %(domain, key, ip_int_to_str(ip_int), collection_id))


def get_ip_header_len(pkg):
    # linux pcap数据包从“any”设备进行捕获，会使用Linux cooked-mode capture (SLL)伪协议，会占16字节
    ip_index = 16
    ip_header_len = struct.unpack('!B', pkg[ip_index:ip_index+1])[0]
    ip_header_len = (ip_header_len & 0b1111) << 2
    return ip_header_len

def get_udp_index(pkg):
    # linux pcap数据包从“any”设备进行捕获，会使用Linux cooked-mode capture (SLL)伪协议，会占16字节
    ip_index = 16
    return ip_index + get_ip_header_len(pkg)

def get_dns_index(pkg):
    # linux pcap数据包从“any”设备进行捕获，会使用Linux cooked-mode capture (SLL)伪协议，会占16字节
    # udp包头8字节
    ip_index = 16
    udp_header_length = 8
    return ip_index + get_ip_header_len(pkg) + udp_header_length


class ipset(Thread):
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def run(self):
        # ip_cache = []
        # cache_len = 0
        while True:
            domain, ip_list = self.queue.get(block = True, timeout=None)
            # print(domain, ip_list)
            for ip_int in ip_list:
                # 处理不通域名解析到同一个ip的时候，有问题
                check_or_add_ipset(domain, ip_int)

class dns(object):
    def __init__(self, dnspkg):
        self.dnspkg = dnspkg
        self.qdcount = 0
        self.ancount = 0
        self.nscount = 0
        self.arcount = 0
        self.current_postition = 0
        self.qname = ''
        self.resolved_ip_list = []

    def get_first_domain_from_index_position(self, i):
        ret = []
        data_len = 0
        while True:
            if self.dnspkg[i:i+1] == b'\x00':
                data_len += 1
                break
            len = struct.unpack('!B', self.dnspkg[i:i+1])[0]
            i += 1
            data_len += 1
            ret.append(self.dnspkg[i:i+len].decode())
            i += len
            data_len += len

        return data_len, '.'.join(ret)

    def get_dns_transaction_id(self):
        # self.transaction_id = 0
        self.transaction_id = struct.unpack('!H', self.dnspkg[self.current_postition:self.current_postition+2])[0]
        self.current_postition += 2

    def get_dns_flags(self):
        dns_flag = struct.unpack('!H', self.dnspkg[self.current_postition:self.current_postition+2])[0]
        self.qr = dns_flag >> 15
        self.rcode = dns_flag & 0b1111
        self.current_postition += 2

    def get_all_count(self):
        self.qdcount, self.ancount, self.nscount, self.arcount = struct.unpack('!4H', self.dnspkg[self.current_postition:self.current_postition+8])
        self.current_postition += 8


    def get_queries(self):
        #self.current_postition = self.query_index
        data_len, self.qname = self.get_first_domain_from_index_position(self.current_postition)
        self.current_postition += data_len
        self.qtype, self.qclass = struct.unpack('!HH', self.dnspkg[self.current_postition:self.current_postition+4])
        self.current_postition += 4


    def get_dns_resolv(self):
        ip_list = []
        for i in range(self.ancount):
            name_lable = struct.unpack('!H', self.dnspkg[self.current_postition:self.current_postition+2])
            self.current_postition += 2
            name_type,name_class,ttl,data_len = struct.unpack('!HHIH', self.dnspkg[self.current_postition:self.current_postition+10])
            self.current_postition += 10
            if name_type == 1:
                ip = struct.unpack('!I', self.dnspkg[self.current_postition:self.current_postition+data_len])[0]
                # ip_split = struct.unpack('!4B', self.dnspkg[self.current_postition:self.current_postition+data_len])
                # ip = ip_split_to_str(ip_split)
                ip_list.append(ip)

            self.current_postition += data_len
        self.resolved_ip_list = ip_list

    def dns_parse(self):
        global transaction_id
        self.get_dns_transaction_id()
        # 同一个包，多个网卡上抓到，通过transaction_id来判断是否分析过
        if self.transaction_id == transaction_id:
            return
        else:
            transaction_id = self.transaction_id
        self.get_dns_flags()
        if self.qr != 1:
            return
        self.get_all_count()
        self.get_queries()
        self.get_dns_resolv()


def dns_callback(timestamp, pkt, *args):
    try:
        dns_index = get_dns_index(pkt)
        dns_info = dns(pkt[dns_index:])
        dns_info.dns_parse()
        # print(str(pkt))
        # print(dns_info.qname, dns_info.resolved_ip_list)
        if dns_info.qname and dns_info.resolved_ip_list:
            dns_queue.put((dns_info.qname, dns_info.resolved_ip_list))
    except:
        print("dnspcap:", str(pkt))


def reload_cfg(signum, frame):
    global domain_collections
    logger.info("capture signal.SIGHUP:%s, begin reload_cfg" % signum)
    # 从域名集合规则和acl规则里获取已使用的id
    used_ids = get_domain_snat_id() | get_acl_id()
    logger.info("reload collection: %s" % ','.join('%s' %id for id in list(used_ids)))
    # 仅仅从配置文件里加载已使用的集合
    domain_collections = get_collection_cfg(used_ids)
    logger.info("end reload_cfg")


logger = logging.getLogger("main")
# 设置默认的日志级别
logger.setLevel(logging.DEBUG)

# 日志路径
logfile = '/var/log/dnspcap/dnspcap.log'
if not os.path.exists('/var/log/dnspcap'):
    os.makedirs('/var/log/dnspcap', 644)
# FileHandler
file_handler = TimedRotatingFileHandler(logfile, when='D', backupCount=7)
# 设置FileHandler的日志级别
file_handler.setLevel(level=logging.INFO)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# 从域名集合规则和acl规则里获取已使用的id
used_ids = get_domain_snat_id() | get_acl_id()
logger.info("load collection: %s" % ','.join('%s' %id for id in list(used_ids)))
# 仅仅从配置文件里加载已使用的集合
domain_collections = get_collection_cfg(used_ids)
# 捕获SIGHUP，重新加载配置
signal.signal(signal.SIGHUP, reload_cfg)
# 检查ipsec是否都已创建
check_ipset()

transaction_id = 0

dns_queue = Queue()
p = ipset(dns_queue)
p.start()

# 抓所有网卡的出方向udp src port 53的包
fpcap = pcap.pcap(name="any", immediate=True)
fpcap.setfilter('udp src port 53')
#fpcap.setdirection(pcap.PCAP_D_OUT)
#fpcap.setdirection(pcap.PCAP_D_IN)

fpcap.loop(0, dns_callback)

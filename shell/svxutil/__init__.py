import os
import socket
import re
import subprocess

SINGLEPORT = 1
MULITPORT = 0
domain_re = re.compile('^([a-zA-Z0-9][-a-zA-Z0-9]{0,62})+(\.[a-zA-Z0-9][-a-zA-Z0-9]{0,62})*\.?$')


class svxError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        print(self.msg + '\n')


def valid_ip(address):
    try:
        socket.inet_aton(address)
        return True
    except:
        return False


def valid_cidr(cidr):
    try:
        address, prefix = cidr.split('/')
        socket.inet_aton(address)
        if 0 <= int(prefix) <= 32:
            return True
        else:
            return False
    except:
        return False


def cidr_format(cidr):
    if not cidr or cidr == 'ANY':
        cidr = '0.0.0.0/0'
    elif '/' not in cidr:
        cidr = cidr + '/32'

    if not valid_cidr(cidr):
        raise svxError('cidr格式错误!')
    return cidr


def port_format(port):
    if port == 'any':
        single_port = SINGLEPORT
    elif port.isdigit():
        if 0 < int(port) < 65536:
            single_port = SINGLEPORT
        else:
            raise svxError('端口必须是1-65535!')
    else:
        single_port = MULITPORT
    return single_port


def get_port_opt(port, d_or_s='null'):
    if not port:
        raise svxError('端口格式错误!')

    if port == 'any':
        port_opt = ''
        single_port = SINGLEPORT
    elif port.isdigit():
        if 0 < int(port) < 65536:
            port_opt = '--%sport %s' %(d_or_s, port)
            single_port = SINGLEPORT
        else:
            raise svxError('端口必须是1-65535!')
    else:
        port_opt = '-m multiport --%sports %s' % (d_or_s, port)
        single_port = MULITPORT
    return (port_opt, single_port)


def is_domain(domain):
    if domain_re.match(domain):
        return True
    else:
        return False


def dns_split(dns):
    tmp = dns.split(':')
    ip = tmp[0]
    if not valid_ip(ip):
        return None, None

    if len(tmp) == 1:
        return ip, 53

    if len(tmp) != 2:
        return None, None

    port = tmp[1]
    if port.isdigit():
        port = int(port)
        if 0 < port < 65536:
            return ip, port

    return None, None


def domain2hex(domain):
    ret = ['']
    for sub_domain in domain.split('.'):
        sub_len = len(sub_domain)
        sub_len_hex = hex(sub_len).replace('0x', '') if sub_len > 15 else '0' + hex(sub_len).replace('0x', '')
        ret.append(sub_len_hex)
        ret.append(sub_domain)

    ret.append('000001')
    ret.append('')

    return '|'.join(ret)


def get_cmd_exitcode(cmd, shell=True):
    try:
        subprocess.check_call(cmd, shell=shell)
        return 0
    except subprocess.CalledProcessError as ex:
        return ex.returncode

#检查vlan是否为1-4094
def is_vlan(vlan_id):
    try:
        if 1 <= int(vlan_id) <= 4094:
            return True
        else:
            return False
    except:
        return False

def format_vlan_list(vlan_list_str):
    vlan_list = []
    for vlan_id in vlan_list_str.split(","):
        if is_vlan(vlan_id):
            vlan_list.append(vlan_id)
        elif "-" in vlan_id:
            try:
                start, end = vlan_id.split("-")
                for i in range(int(start), int(end) + 1):
                    vlan_list.append(str(i))
            except Exception as e:
                continue
    return vlan_list

#检查vlan是否为1-4094
def is_switch_port(port):
    try:
        if 1 <= int(port) <= 48:
            return True
        else:
            return False
    except:
        return False

def format_switch_port_list(port_list_str):
    port_list = []
    for port in port_list_str.split(","):
        if is_switch_port(port):
            port_list.append(port)
        elif "-" in port:
            try:
                start, end = port.split("-")
                for i in range(int(start), int(end) + 1):
                    port_list.append(str(i))
            except Exception as e:
                continue
    return port_list

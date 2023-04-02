
import os
import sys

NetworkConf = "/etc/xx/conf.d/network.conf"

def get_interface_dict_by_file():
    interface_dict = {}
    if os.path.exists(NetworkConf):
        abys = open(NetworkConf, 'r', encoding='UTF-8')
        try:
            for line in abys.readlines():
                key, value = line.strip().split('=')
                if key.startswith("#"):
                    continue
                interface_dict[key.strip()] = value.strip()
        finally:
            abys.close()
    return interface_dict

def get_interface_by_ifname(interface_dict, ifname):
    ifname = ifname.upper()
    # interface_dict = get_network_interfaces_by_file()
    if ifname.startswith("WAN"):
        return interface_dict.get(ifname, "").lower()
    elif ifname.startswith('LAN'):
        return interface_dict.get(ifname, "").lower()
    elif  ifname.startswith("MOBILE"):
        return interface_dict.get(ifname, "").lower()
    elif ifname.startswith("WIFI"):
        return interface_dict.get(ifname, "").lower()
    elif ifname.startswith("VLAN"):
        return ifname.lower()
    elif ifname.startswith("BOND"):
        return ifname.lower()
    else:
        return ""

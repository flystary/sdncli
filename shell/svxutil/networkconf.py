wan_to_interface = {
    "WAN1": "enp1s0",
    "WAN2": "enp2s0"
}

lan_to_interface = {
    "LAN1":  "enp3s0",
    "LAN2":  "enp4s0",
    "LAN3":  "enp5s0",
    "LAN4":  "enp6s0",
    "LAN5":  "enp7s0",
    "LAN6":  "enp8s0"
}

mobile_to_interface = {
    "MOBILE4G": "usb4g",
    "MOBILE5G": "usb5g"
}

wifi_to_interface = {
    "WIFI_IFNAME": "wlan0"
}

def get_interface_by_net(ifname):
    ifname = ifname.upper()
    if ifname.startswith("WAN"):
        return wan_to_interface.get(ifname, "").lower()
    elif ifname.startswith('LAN'):
        return lan_to_interface.get(ifname, "").lower()
    elif  ifname.startswith("MOBILE"):
        return mobile_to_interface.get(ifname, "").lower()
    elif ifname.startswith("WIFI"):
        return wifi_to_interface.get(ifname, "").lower()
    elif ifname.startswith("VLAN"):
        return ifname.lower()
    elif ifname.startswith("BOND"):
        return ifname.lower()
    else:
        return ""

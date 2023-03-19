dhgroup = {
    1: "modp768",
    2: "modp1024",
    5: "modp1536",
    14: "modp2048",
    15: "modp3072",
    16: "modp4096",
    17: "modp6144",
    18: "modp8192",
    19: "ecp256",
    20: "ecp384",
    21: "ecp521",
    22: "modp1024s160",
    23: "modp2048s224",
    24: "modp2048s256",
    25: "ecp192",
    26: "ecp224",
    27: "ecp224bp",
    28: "ecp256bp",
    29: "ecp384bp",
    30: "ecp512bp",
    31: "curve25519",
    32: "curve448"
}

def dhrelation(dh_group):
    dhlist = []
    num = len(dh_group)
    try:
        if 0 < num <= 3:
            for dh in dh_group:
                dhlist.append(dhgroup[dh])
            return dhlist
        else:
            return dhlist
    except:
        return dhlist


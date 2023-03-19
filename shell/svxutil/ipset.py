import subprocess

def get_all_ipsetname():
    ipsets = []
    cmd = "ipset list |grep '^Name'"
    _, result = subprocess.getstatusoutput(cmd)
    for line in result.splitlines():
        tmp = line.split()
        if len(tmp) == 2:
            ipsets.append(tmp[1])

    return ipsets


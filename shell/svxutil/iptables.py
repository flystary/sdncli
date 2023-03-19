import os
import sys
import svxutil
import subprocess
import svxutil.baseconf

# 备份iptables
def backup_iptables():
    if os.path.exists('/tmp/iptables'):
        os.remove('/tmp/iptables')
    svxutil.get_cmd_exitcode('/bin/cp %s /tmp' % svxutil.baseconf.iptables_conf)
    if not os.path.exists('/tmp/iptables'):
        sys.stderr.write('iptables备份失败')
        return False
    else:
        return True


# 还原iptables
def restore_iptables():
    if os.path.exists('/tmp/iptables'):
        svxutil.get_cmd_exitcode('/bin/cp /tmp/iptables %s' % svxutil.baseconf.iptables_conf)
    svxutil.get_cmd_exitcode('systemctl restart iptables')


# 老snat规则index
def get_snat_rules(chain):
    r = []
    _, result = subprocess.getstatusoutput("iptables -n -t nat -L %s --line-numbers 2>/dev/null" % chain)
    for line in result.splitlines():
        tmp = line.split()
        if len(tmp) > 2:
            index = tmp[0]
            act = tmp[1]
            if act in ['MASQUERADE', 'SNAT', 'LOG'] and index.isdigit():
                r.append(int(index))
    r.sort(reverse=True)
    return r


def check_dns_redirect_rule():
    status = svxutil.get_cmd_exitcode("iptables -t nat -nL dnsRedirect &>/dev/null")
    if status != 0:
        svxutil.get_cmd_exitcode("iptables -t nat -N dnsRedirect")

    status = svxutil.get_cmd_exitcode(
        "iptables -t nat -C PREROUTING -p udp -m udp --dport 53 -m u32 --u32 '0x0>>0x16&0x3c@0x8>>0xf&0x1=0x0' -j dnsRedirect &>/dev/null")
    if status != 0:
        svxutil.get_cmd_exitcode(
            "iptables -t nat -A PREROUTING -p udp -m udp --dport 53 -m u32 --u32 '0x0>>0x16&0x3c@0x8>>0xf&0x1=0x0' -j dnsRedirect")

    status = svxutil.get_cmd_exitcode("iptables -t nat -F dnsRedirect-intercept")
    if status != 0:
        svxutil.get_cmd_exitcode("iptables -t nat -N dnsRedirect-intercept")

    status = svxutil.get_cmd_exitcode("iptables -t nat -C dnsRedirect -j dnsRedirect-intercept")
    if status != 0:
        svxutil.get_cmd_exitcode("iptables -t nat -A dnsRedirect -j dnsRedirect-intercept")

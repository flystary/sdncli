#!/usr/bin/python3
# encoding:utf-8

import os
import sys
import getopt
import subprocess
import ruamel.yaml

# 获取命令参数
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hg:c:', ["help", "status=","category="])
except getopt.GetoptError as e:
    print(e.msg)
    sys.exit(1)
       
# 读取
for o, a in opts:
    if o in ("-s", "--status"):
        status = a
    
    if o in ("-c", "--category"):
        category = a
    else:
        category = ''
   
rules_list = []
rules_path = '/etc/suricata/rules'
suricata_file = '/etc/suricata/suricata.yaml'

if not os.path.exists(suricata_file):
    sys.exit(99)

if not os.path.exists(rules_path):
    os.mkdir(rules_path)

if category:
    for v in category.split('|'):
        if  v:
            rules_list.append(v)
        else:
            continue

if status in ["start","stop"]:
    if status == "stop":
        rules_list = []
        
        try:
            num = subprocess.getoutput("iptables -t mangle -L  FORWARD  | grep NFQUEUE | wc -l")
            if int(num) > 0:
                subprocess.check_call("iptables -t mangle -D FORWARD -j NFQUEUE --queue-num 0 --queue-bypass", shell=True)
                subprocess.check_call("iptables-save > /etc/sysconfig/iptables", shell=True)
            subprocess.check_call("systemctl stop ips_event.service;systemctl disable ips_event.service", shell=True)
        except:
            pass
    else:
        try:
            num = subprocess.getoutput("iptables -t mangle -L  FORWARD  | grep NFQUEUE | wc -l")
            if int(num) == 0:
                subprocess.check_call("iptables -t mangle -I  FORWARD 1 -j NFQUEUE  --queue-bypass", shell=True)
                subprocess.check_call("iptables-save > /etc/sysconfig/iptables", shell=True)
            subprocess.check_call("systemctl restart ips_event.service;systemctl enable ips_event.service", shell=True)
        except:
            pass
else:
    sys.stderr("status类型错误")
    sys.exit(2)

yaml = ruamel.yaml.YAML()
yaml.indent(mapping=2, sequence=4, offset=2)             
try:
    code = yaml.load(open(suricata_file, 'r'))
except:
    sys.stderr("load suricata conf file error")
    sys.exit(9)

code['rule-files'] = ['xnetworks.rules']

for i in rules_list:
    rules = '%s.rules' % i
    code['rule-files'].append(rules)

try:
    yaml.dump(code, open(suricata_file, 'w'))
except:
    sys.stderr("dump suricata conf file error")
    sys.exit(9)

try: 
    subprocess.check_call('systemctl restart suricata', shell=True)
except:
    sys.exit(2)
    

sys.exit(0)

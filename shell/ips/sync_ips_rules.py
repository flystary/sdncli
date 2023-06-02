#!/usr/bin/python3
# encoding:utf-8

import os
import sys
import getopt
import time
import subprocess



# 获取命令参数
try:
    opts, args = getopt.getopt(sys.argv[1:], 'hm:u:', ["help", "md5=","downurl="]
    )
except getopt.GetoptError as e:
    print(e.msg)
    sys.exit(1)
       
# 读取
for o, a in opts:
    if o in ("-m", "--md5"):
        md5 = a
    if o in ("-u", "--downurl"):
        url= a
    
ips_sync_path = '/var/lib/suricata/rules'

if not os.path.exists(ips_sync_path):
    os.mkdir(ips_sync_path)
    

times = time.strftime("%Y%m%d%H%M%S", time.localtime()) 
ips_gz_file = '/tmp/ips.%s.tar.gz' % times
try:
    subprocess.check_call('wget -c %s -O %s' % (url, ips_gz_file), shell=True)
except:
    sys.stderr("No wget zip file")
    sys.exit(2)

getout = subprocess.getoutput('md5sum %s' % (ips_gz_file))

if md5 == getout.split('  ')[0]:
    #清空rules
    for _, _, files in os.walk(ips_sync_path):
        for file in files:
            if file != "xnetworks.rules":
                os.remove('%s/%s' % (ips_sync_path, file))
    try:
        subprocess.check_call('tar -zxf %s -C  %s'  % (ips_gz_file,ips_sync_path), shell=True)
    except:
        sys.stderr("tar file error")
        sys.exit(3)
else:
    sys.stderr("md5 error")
    sys.exit(4)


os.remove(ips_gz_file)
sys.exit(0)

#!/usr/bin/python3
#encoding:utf-8

import os
import sys
import json
#import urllib2
import urllib.request as urllib2

url = 'http://myip.ipip.net/json'
request = urllib2.Request(url=url)

try:
    response = urllib2.urlopen(request, timeout=30)
except:
    sys.exit(0)

httpcode = response.code

if httpcode != 200:
    response.close()
    sys.exit(0)

result = json.loads(response.read())
response.close()

try:
    isp = result['data']['location'][-1]
except:
    sys.exit(0)

if isp == u'电信':
    isp_code = 1
elif isp == u'联通':
    isp_code = 2
elif isp == u'移动':
    isp_code = 3
else:
    isp_code = 4

print(isp_code)
sys.exit(0)


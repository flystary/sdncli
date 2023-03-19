import os
import re
import sys
import json
#import logging
import requests

USERNAME="7xnetworks"
PASSWORD="Abcd@1234"
BASEURL="http://127.0.0.1:8000/api/v1"
isActiveSWGService="systemctl is-active swg.service"

#logger = logging.getLogger("SWG")
# 设置默认的日志级别
#logger.setLevel(logging.ERROR)

# 日志路径
logfile = '/var/log/swg/swg.log'
if not os.path.exists('/var/log/swg'):
    os.makedirs('/var/log/swg', 755)

# FileHandler
#file_handler = logging.FileHandler(logfile, 'a',encoding='utf-8')
# 设置FileHandler的日志级别
#file_handler.setLevel(level=logging.DEBUG)
# formatter = logger.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
#formatter = logging.Formatter('%(asctime)s %(filename)s line:%(lineno)d %(levelname)s %(message)s %(process)s')
#file_handler.setFormatter(formatter)
#logger.addHandler(file_handler)

def checkUser(username):
    if re.search(r"\W", username) is None:

        if 3 <= len(username) <= 20 :
            return True
        else:
            return False

def checkPassword(password):
    if len(password) >= 6:
        return True
    else:
        return False

class Interface(object):
    def __init__(self, username, password, url):
        if checkPassword(password) and checkUser(username):
            self.username = username
            self.password = password
        else:
            raise Exception
        self.headers = {
                    'content-type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:22.0) Gecko/20100101 Firefox/22.0',
                    'username': self.username,
                    "password": self.password,
        }
        self.url = url
        #self.logger = logging.getLogger("SWG.Interface")
    #发送数据
    def sendJson(self, data):
        sendData = json.dumps(data)
        try:
            r = requests.post(url=self.url, headers=self.headers, data=sendData)
        except Exception as e:
            #print(e)
            sys.exit(22)

        # 转成json
        if r.status_code == 200:
            msg_json = r.json()
        else:
            sys.exit(12)
        if msg_json["code"] == 0 :
            #self.logger.info("send json success: %s %s %s code:%s data:%s message:%s" % (self.url, sendData, r, msg_json["code"], msg_json["data"], msg_json["message"]))
            return True
        else:
            #记录不成功的数据 url data code
            #self.logger.warning("send json failed: %s %s %s code:%s data:%s message:%s" % (self.url, sendData, r, msg_json["code"], msg_json["data"], msg_json["message"]))
            return False
    #获取数据
    def getJson(self):
        try:
            r = requests.get(url=self.url, headers=self.headers)
        except Exception as e:
            #print(e)
            sys.exit(33)

        # 转成json
        if r.status_code == 200:
            msg_json = r.json()
        else:
            sys.exit(11)

        if msg_json["code"] == 0:
            #self.logger.info("get json success: %s %s code:%s data:%s message:%s" % (self.url, r, msg_json["code"], msg_json["data"], msg_json["message"]))
            return True, msg_json["data"]
        #16 ad数据未同步
        elif msg_json["code"] == 16:
            #self.logger.warning("get json success: %s %s code:%s data:%s message:%s" % (self.url, r, msg_json["code"], msg_json["data"], msg_json["message"]))
            return True, msg_json["data"]
        else:
            #self.logger.warning("get json failed: %s %s code:%s data:%s message:%s" % (self.url, r, msg_json["code"], msg_json["data"], msg_json["message"]))
            return False, []


class Vlan(Interface):
    def __init__(self, username, password, url, mode="vlan"):
        super(Vlan, self).__init__(username, password, url)
        self.mode = mode
        self.url = '%s/%s' % (url, self.mode)
        #self.logger = logging.getLogger("SWG.Interface.Vlan")

    def send_vlan(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

class ObjIdentifyEditAd(Interface):
    def __init__(self, username, password, url, mode="obj_identify_edit_ad"):
        super(ObjIdentifyEditAd, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.ObjIdentifyEditAd")
        if mode == "obj_identify_edit_ad":
            self.url = '%s/obj/identify/editad' % self.url

    def send_obj_identify_edit_ad(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

class AccessSyncAuthRule(Interface):
    def __init__(self, username, password, url, mode="access_sync_auth_rule"):
        super(AccessSyncAuthRule, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.AccessSyncAuthRule")
        if mode == "access_sync_auth_rule":
            self.url = '%s/access/sync/authrule' % self.url

    def send_access_sync_auth_rule(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

class AccessAuthEditSettings(Interface):
    def __init__(self, username, password, url, mode="access_edit_auth_settings"):
        super(AccessAuthEditSettings, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.AccessAuthEditSettings")
        if mode == "access_edit_auth_settings":
            self.url = '%s/access/editauthsettings' % self.url

    def send_access_edit_auth_settings(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

class ObjIdentifyMode(Interface):
    def __init__(self, username, password, url, mode="obj_identify_mode"):
        super(ObjIdentifyMode, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.ObjIdentifyMode")
        if self.mode == "obj_identify_mode":
            self.url = '%s/obj/identify/mode' % self.url

    def send_obj_identify_mode(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

class ObjGetAdFull(Interface):
    def __init__(self, username, password, url, mode="obj_get_adfull"):
        super(ObjGetAdFull, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.ObjGetAdFull")
        if self.mode == "obj_get_adfull":
            self.url = '%s/obj/getadfull' % self.url

    def get_obj_get_adfull(self):
        status, data = self.getJson()
        if status:
            return data
        sys.exit(11)

class ObjSyncFull(Interface):
    def __init__(self, username, password, url, mode="obj_sync_full"):
        super(ObjSyncFull, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.ObjSyncFull")
        if self.mode == "obj_sync_full":
            self.url = '%s/obj/sync/full' % self.url

    def send_obj_sync_full(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

class SyncFreezingObjects(Interface):
    def __init__(self, username, password, url, mode="freezing_objects"):
        super(SyncFreezingObjects, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.SyncFreezingObjects")
        if mode == "freezing_objects":
            self.url = '%s/freezing-objects' % self.url

    def send_sync_freezing_objects(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

# /api/v1/url-auth/sync-policies
class SyncApplicationPolicies(Interface):
    def __init__(self, username, password, url, mode="application_policies"):
        super(SyncApplicationPolicies, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.SyncApplicationPolicies")
        if mode == "application_policies":
            self.url = '%s/access/sync/ctrlrule' % self.url

    def send_sync_application_policies(self, data):
        if self.sendJson(data):
            return True
        else:
            return False

class IpMacGetRecognizedObject(Interface):
    def __init__(self, username, password, url, mode="ip_mac_recognized_object"):
        super(IpMacGetRecognizedObject, self).__init__(username, password, url)
        self.mode = mode
        #self.logger = logging.getLogger("SWG.Interface.IpMacGetRecognizedObject")
        if mode == "ip_mac_recognized_object":
            self.url = '%s/ip-mac/recognized_object' % self.url

    def get_ip_mac_recognized_object(self):
        status, data = self.getJson()
        if status:
            return data
        sys.exit(11)

class ObjGetTerms(Interface):
    def __init__(self, username, password, url, mode="obj_get_terms"):
        super(ObjGetTerms, self).__init__(username, password, url)
        #self.logger = logging.getLogger("SWG.Interface.ObjGetTerms")
        self.mode = mode
        if mode == "obj_get_terms":
            self.url = '%s/obj/getterms' % self.url

    def get_obj_terms(self):
        status, data = self.getJson()
        if status:
            return data
        sys.exit(11)

class GetFreezingObjects(Interface):
    def __init__(self, username, password, url, mode="get_freezing_objects"):
        super(GetFreezingObjects, self).__init__(username, password, url)
        #self.logger = logging.getLogger("SWG.Interface.GetFreezingObjects")
        self.mode = mode
        if mode == "get_freezing_objects":
            self.url = '%s/get-freezing-objects' % self.url

    def get_freezing_objects(self):
        status, data = self.getJson()
        if status:
            return data
        sys.exit(11)

class GetApplicationOperationLogs(Interface):
    def __init__(self, username, password, url, mode="get_application_operation_logs"):
        super(GetApplicationOperationLogs, self).__init__(username, password, url)
        #self.logger = logging.getLogger("SWG.Interface.GetApplicationOperationLogs")
        self.mode = mode
        if mode == "get_application_operation_logs":
            self.url = '%s/app-operation-logs' % self.url

    def get_application_operation_logs(self):
        status, data = self.getJson()
        if status:
            return data
        sys.exit(11)

#!/usr/bin/python3

import os
import sys
import time
import telnetlib
import re
import logging
import sched

ip=sys.argv[1]
input_bytes_match = re.compile("input, (\d+) bytes", re.MULTILINE)
output_bytes_match = re.compile("output, (\d+) bytes", re.MULTILINE)
five_minutes_input_rate = re.compile(
    "5 minutes input rate (\d+) bits", re.MULTILINE)
five_minutes_output_rate = re.compile(
    "5 minutes output rate (\d+) bits", re.MULTILINE)


logger = logging.getLogger("main")
# 设置默认的日志级别
logger.setLevel(logging.DEBUG)

# 日志路径
logfile = '/var/log/switch/%s.log' % ip
if not os.path.exists('/var/log/switch'):
    os.makedirs('/var/log/switch', 755)
# FileHandler
file_handler = logging.FileHandler(logfile, 'a')
# 设置FileHandler的日志级别
file_handler.setLevel(level=logging.WARNING)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


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


class Terminel(object):
    def __init__(self, ip, port=23, timeout_login=3, timeout_cmd=3):
        self.ip = ip
        self.port = port
        self.timeout_login = timeout_login
        self.timeout_cmd = timeout_cmd
        self.logger = logging.getLogger("main.telnet")
        self.client = None
        if ip:
            self.connect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        try:
            # telnet connect to switch
            self.logger.info("telnet to switch %s:%s" % (self.ip, self.port))
            client = telnetlib.Telnet(self.ip, self.port, self.timeout_login)
        except TimeoutError as e:
            self.logger.warning("telnet to switch timeout!")
            self.client = None
            return
        except Exception as e:
            self.logger.warning("telnet to switch failed! %s" % e.message)
            self.client = None
            return

        try:
            # wait for Username:
            client.read_until(b'Username:', self.timeout_login)
            # input username
            client.write(b'admin\r\n')
            # wait for Password:
            client.read_until(b'Password:', self.timeout_cmd)
            # input password
            client.write(b'admin\r\n')
            # 等待登录成功
            client.read_until(b'Switch#', self.timeout_cmd)
        except:
            client.close()
            self.client = None
            return

        self.logger.info("login switch success!")
        self.client = client

    def disconnect(self):
        if not self.client:
            return

        try:
            self.client.write(b'end\r\n')
            self.client.write(b'exit\r\n')
            self.client.write(b'exit\r\n')
            self.client.close()
            self.logger.warning("disconnect switch success!")
        except:
            return

    #重新连接
    def telnet_reconnect(self):
        self.disconnect()
        self.connect()

    #执行单个命令
    def exec_cmd(self, cmd):
        try:
            if not isinstance(cmd, bytes):
                cmd = cmd.encode('ascii')
            self.client.read_very_eager()
            self.client.write(cmd)
            ret = self.client.read_until(b'Switch#', self.timeout_cmd).decode()
            return (True,ret)
        except EOFError as e:
            if e.message == "telnet connection closed":
                self.client = None
        except Exception as e:
            return (False, "")

    # 执行多个命令
    def exec_cmds(self, cmds):
        # try:
        for cmd in cmds:
            if not isinstance(cmd, bytes):
                cmd = cmd.encode('ascii')
            self.client.read_very_eager()
            self.client.write(cmd)

        ret = self.client.read_until(b'Switch#', self.timeout_cmd).decode()
        return (True, ret)

    def exec_cmd_has_more(self, cmd):
        try:
            if not isinstance(cmd, bytes):
                cmd = cmd.encode('ascii')
            self.client.read_very_eager()
            self.client.write(b'terminal length 0\r\n')
            self.client.read_until(b'Switch#', self.timeout_cmd)
            self.client.write(cmd)

        except EOFError as e:
            if e.message == "telnet connection closed":
                self.client = None
        except Exception as e:
            return (False, "")
        # 清理未读取的信息
        # self.client.read_very_eager()
        ret = self.client.read_until(b'Switch#', 5).decode()
        # expect = []
        # expect.append(b'--More--')
        # # 清理未读取的信息
        # self.client.read_very_eager()
        # ret = ""

        # while True:
        #     is_expect, _ , text = self.client.expect(expect, 3)
        #     ret = ret + text.decode()

        #     if is_expect == 0:
        #         self.client.write(b" ")
        #     else:
        #         break

        return (True,ret)


class Interface(object):
    def __init__(self, name, interface_id, eth_type, terminel, interface_info=""):
        self.name = name
        self.interface_id = interface_id
        self.terminel = terminel
        self.interface_info = interface_info
        self.eth_type = eth_type
        self.eth_status_match = re.compile(
            "%s%s is (\w+)" % (eth_type,interface_id), re.MULTILINE)
        self.network_info_cmd = 'show interfaces %s %s\r\n' % (eth_type, interface_id)
        self.vlan_info_cmd = 'show interfaces switchport %s %s\r\n' % (eth_type, interface_id)
        self.logger = logging.getLogger("main.switch.interface")

        self.info = {
            "name": name,
            "eth_type": eth_type,
            "id": interface_id,
            "eth_stutus": "down",
            "portmode": "access",
            "trunking_vlans": [],
            "native_vlan": 0,
            "input_bytes": 0,
            "output_bytes": 0,
            "last_input_rate": 0,
            "last_input_rate": 0,
            "updatetime": 0
        }

    def get_interface_id(self):
        return self.interface_id

    def get_eth_status(self):
        if not self.interface_info:
            return "down"

        result = self.eth_status_match.search(self.interface_info)

        if result and result.groups():
            if result.groups()[0] == "up":
                return "up"

        return "down"

    def get_input_bytes(self):
        if not self.interface_info:
            return 0

        result = input_bytes_match.search(self.interface_info)
        if result and result.groups():
            return int(result.groups()[0])
        else:
            return 0

    def get_output_bytes(self):
        if not self.interface_info:
            return 0

        result = output_bytes_match.search(self.interface_info)
        if result and result.groups():
            return int(result.groups()[0])
        else:
            return 0

    def get_last_5min_input_rate(self):
        if not self.interface_info:
            return 0

        result = five_minutes_input_rate.search(self.interface_info)
        if result and result.groups():
            return int(result.groups()[0])
        else:
            return 0

    def get_last_5min_output_rate(self):
        if not self.interface_info:
            return 0

        result = five_minutes_output_rate.search(self.interface_info)
        if result and result.groups():
            return int(result.groups()[0])
        else:
            return 0

    def get_interface_mode(self):
        success, ret = self.terminel.exec_cmd(self.vlan_info_cmd)
        if success:
            self.logger.info("get_interface_mode %s %s exec cmd success" % (self.eth_type, self.interface_id))
        else:
            self.logger.warning("get_interface_mode %s %s exec cmd failed" % (self.eth_type, self.interface_id))
            return

        for line in ret.splitlines():
            if ":" not in line:
                continue

            tmp = line.strip().split(":")
            mode = 'access'
            native_vlan = 7
            self.logger.info("get_interface_mode %s %s ret: %s" % (self.eth_type, self.interface_id, tmp))

            if 'Port Mode' in tmp[0]:
                mode = tmp[1].strip().lower()
                self.info["portmode"] = mode
                self.logger.info("get_interface_mode %s %s mode is %s" % (self.eth_type, self.interface_id, mode))
            elif 'Ingress UnTagged VLAN' in tmp[0]:
                native_vlan = tmp[1].strip()
                if is_vlan(native_vlan):
                    self.info["native_vlan"] = native_vlan
                self.logger.info("get_interface_mode %s %s native_vlan is %s" % (self.eth_type, self.interface_id, native_vlan))
                self.logger.info("get_interface_mode %s %s native_vlan is %s" % (self.eth_type, self.interface_id, self.info["native_vlan"]))
            elif 'Trunking VLANs Enabled' in tmp[0]:
                trunking_vlans = tmp[1].strip()
                self.info["trunking_vlans"] = format_vlan_list(trunking_vlans)
                self.logger.info("get_interface_mode %s %s trunking_vlans is %s" % (self.eth_type, self.interface_id, trunking_vlans))
                self.logger.info("get_interface_mode %s %s trunking_vlans is %s" % (self.eth_type, self.interface_id, self.info["trunking_vlans"]))
            else:
                continue

        self.logger.info("get_interface_mode %s %s info:%s" %  (self.eth_type, self.interface_id, self.info))


    def get_interface_mode_format(self):
        self.get_interface_mode()
        portmode = self.info["portmode"]
        if portmode == 'access':
            vlan_str = self.info["native_vlan"] if self.info["native_vlan"] else "0"
        else:
            trunking_vlans = self.info["trunking_vlans"]
            if trunking_vlans:
                vlan_str = '|'.join(trunking_vlans)
            else:
                vlan_str = "0"

        return "%s %s %s %s" % (
            self.interface_id,
            self.name,
            self.info["portmode"],
            vlan_str,
        )

    def get_interface_stat(self):
        now = time.time()
        success, ret = self.terminel.exec_cmd(self.network_info_cmd)

        if success:
            self.interface_info = ret
            self.logger.info("get_interface_stat %s %s success" % (self.eth_type, self.interface_id))
        else:
            self.interface_info = ""
            self.logger.warning("get_interface_stat %s %s failed" % (self.eth_type, self.interface_id))

        last_input_bytes = self.info["input_bytes"]
        last_output_bytes = self.info["output_bytes"]
        last_time = self.info["updatetime"]

        self.info["eth_stutus"] = self.get_eth_status()
        self.info["input_bytes"] = self.get_input_bytes()
        self.info["output_bytes"] = self.get_output_bytes()
        self.info["updatetime"] = now
        if last_time <= 0:
            last_input_rate = self.get_last_5min_input_rate()
            last_output_rate = self.get_last_5min_output_rate()
        else:
            input_bytes_diff = self.info["input_bytes"] - last_input_bytes
            if input_bytes_diff >= 0:
                last_input_rate = 8 * input_bytes_diff / (now - last_time)
            else:
                last_input_rate = self.get_last_5min_input_rate()

            output_bytes_diff = self.info["output_bytes"] - last_output_bytes
            if output_bytes_diff >= 0:
                last_output_rate = 8 * output_bytes_diff / (now - last_time)
            else:
                last_output_rate = self.get_last_5min_output_rate()

        self.info["last_input_rate"] = int(last_input_rate)
        self.info["last_output_rate"] = int(last_output_rate)

    def get_interface_stat_format(self):
        self.get_interface_stat()

        return "%s %s %s %s %s" %(
            self.interface_id,
            self.name,
            self.info["eth_stutus"],
            self.info["last_input_rate"],
            self.info["last_output_rate"]
        )


class Mirror(object):
    def __init__(self, interface_id, terminel) -> None:
        self.terminel = terminel
        self.interface_id = interface_id
        self.cmd = "show mirror session %s" % interface_id
        self.logger = logging.getLogger("main.switch.mirror")
        self.source = "null"
        self.target = "null"


    def get_span_info(self):
        # 命令输出格式:
        # Session 1 Configuration
        # Source RX Port    : gi7-8
        # Source TX Port    : gi7-8
        # Destination port  : gi10
        # Ingress State: disabled
        success, ret = self.terminel.exec_cmd(self.cmd)
        if success:
            self.interface_info = ret
            self.logger.info("get_span_info mirror session %s success" % (self.interface_id))
        else:
            self.interface_info = ""
            self.logger.warning("get_span_info mirror session %s failed" % (self.interface_id))

        for line in ret.splitlines():
            if ":" not in line:
                continue

            tmp = line.strip().split(":")

            if 'Source RX Port' in tmp[0]:
                source = tmp[1].strip().lower().replace("gi", "")
                self.source = "|".join(format_vlan_list(source))
                self.logger.info("get_span_info mirror session %s source is %s" % (self.interface_id, source))
            elif 'Destination port' in tmp[0] and "Not Config" not in tmp[1]:
                target = tmp[1].strip().lower().replace("gi", "")
                self.target = target
                self.logger.info("get_span_info mirror session %s target is %s" % (self.interface_id, target))

    def get_span_info_format(self):
        self.get_span_info()
        return "%s %s %s" % (
            self.interface_id,
            self.source,
            self.target
        )


class Switch(object):
    def __init__(self, ip):
        self.ip = ip
        # 实例化terminel
        self.terminel = Terminel(ip)
        self.input_bytes_match = re.compile("input, (\d+) bytes", re.MULTILINE)
        self.output_bytes_match = re.compile("output, (\d+) bytes", re.MULTILINE)
        self.five_minutes_input_rate = re.compile("5 minutes input rate (\d+) bits", re.MULTILINE)
        self.five_minutes_output_rate = re.compile("5 minutes output rate (\d+) bits", re.MULTILINE)
        self.switch_path="/usr/local/*/conf.d/switch/%s"  % ip

        self.logger = logging.getLogger("main.switch")

        #实例化switch的eth口
        self.interface = {}
        for index in range(1, 17):
            name = "ETH%s" % index
            self.interface[name] = Interface(name, index, "GigabitEthernet", self.terminel)
            self.logger.debug("instantiate switch %s %s GigabitEthernet%s" %(self.ip, name, index))

        #实例化bond口
        for index in range(1, 5):
            name = "LAG%s" % index
            self.interface[name] = Interface(name, index, "LAG", self.terminel)
            self.logger.debug("instantiate switch %s %s LAG%s" %(self.ip, name, index))

        #实例化span口
        # self.mirror = {}
        # for index in range(1, 5):
        #     self.mirror[index] = Mirror(index, self.terminel)
        #     self.logger.debug("instantiate switch mirror session %s SPAN%s" %(self.ip, index))

        # self.lancount = len(self.interface)


    def update_all_interface(self):
        if not os.path.exists(self.switch_path):
            os.makedirs(self.switch_path, 755)

        switch_interface_stat = []
        # switch_interface_mode = []

        for interface in self.interface.values():
            # 通过showrunning配置文件读取
            # switch_interface_mode.append(interface.get_interface_mode_format())
            switch_interface_stat.append(interface.get_interface_stat_format())

        # fp_mode = open("%s/%s" % (self.switch_path, 'eth.mode'), 'w')
        # for line in switch_interface_mode:
        #     fp_mode.write(line + "\n")
        # fp_mode.close()

        fp_stat = open("%s/%s" % (self.switch_path, 'eth.info'), 'w')
        for line in switch_interface_stat:
            fp_stat.write(line + "\n")
        fp_stat.close()


    def show_running(self):
        success, ret = self.terminel.exec_cmd_has_more('show running-config\r\n')
        self.logger.debug("switch show running: %s " %(ret))
        if not success:
            return

        if not os.path.exists(self.switch_path):
            os.makedirs(self.switch_path, 755)

        fp = open(self.switch_path + "/running_config", 'w')
        for line in ret.splitlines():
            if "!" not in line and "More" not in line:
                fp.write(line + '\n')
        fp.close


def crontab():
    # 启动新的定时器
    cron.enter(60, 0, crontab, ())
    # 执行真正的任务
    switch.update_all_interface()
    #switch.show_running()


# 初始化switch
switch = Switch(ip)
cron = sched.scheduler(time.time, time.sleep)
# 第一次任务，马上执行
cron.enter(0, 0, crontab, ())
cron.run()

sys.exit(0)

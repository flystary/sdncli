import os
import sys
import subprocess
import telnetlib


def update_running_config(mgmt_ip):
    try:
        subprocess.check_call("/usr/local/*/lib/switch_showrun.sh %s" % mgmt_ip, shell=True)
    except:
        pass


class Terminel(object):
    def __init__(self, ip, port=23, timeout_login=3, timeout_cmd=3):
        self.ip = ip
        self.port = port
        self.timeout_login = timeout_login
        self.timeout_cmd = timeout_cmd
        self.client = None
        if ip:
            self.connect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        try:
            # telnet connect to switch
            client = telnetlib.Telnet(self.ip, self.port, self.timeout_login)
        except TimeoutError as e:
            self.client = None
            return
        except Exception as e:
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

        self.client = client

    def disconnect(self):
        if not self.client:
            return

        try:
            self.client.write(b'end\r\n')
            self.client.write(b'exit\r\n')
            self.client.write(b'exit\r\n')
            self.client.close()
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
            # 清理未读取的信息
            self.client.read_very_eager()
            self.client.write(b'terminal length 0\r\n')
            self.client.read_until(b'Switch#', self.timeout_cmd)
            self.client.write(cmd)

        except EOFError as e:
            if e.message == "telnet connection closed":
                self.client = None
        except Exception as e:
            return (False, "")

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

class Switch(object):
    def __init__(self, ip, cmd):
        self.ip  = ip
        self.cmd = cmd
        self.file_name = cmd.replace(" ", "_").replace("-", "_")
        # 实例化terminel
        self.terminel = Terminel(ip)
        self.switch_path="/usr/local/*/conf.d/7xswitch/%s/"  % ip
    def show_running(self):
        cmd = self.cmd + "\r\n"

        success, ret = self.terminel.exec_cmd_has_more(cmd)
        if not success:
            return

        if not os.path.exists(self.switch_path):
            os.makedirs(self.switch_path, 755)

        fp = open(self.switch_path + self.file_name, 'w')
        for line in ret.splitlines():
            if "!" not in line and "More" not in line:
                fp.write(line + '\n')
        fp.close

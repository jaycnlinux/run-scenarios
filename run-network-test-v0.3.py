#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = 'chengxiang'
# version: v0.2
# date: 20190328
# 修改内容：引进Class对象编程


import sys
import os
import time
import subprocess
#import pexpect
import re
import copy
import logging
import gc
import math


# 全局变量 源IP、目标IP列表，流数
OB_HOST = '192.168.0.209'
SRC_HOST = '192.168.0.209'
DST_HOST = '192.168.0.147'
FLOWS = 0       # 0表示自动设置，否则表示手动
FLOW_STEP = {'1U': 16, '16U': 32, '32U': 64, '60U': 128}
RETURN_OK = 0
RETURN_FAIL = -1
LOG_FILE = ''
ORDER_STEP = 0  # 依次测试，N:N的场景
ORDER_ALL = 1   # 同时测试，N:N的场景
DEBUG_MODE = False  # 调试模式
BASE_DIR = 'log'
logger = None   # 日志对象
TASK_APP = ''
NIC_NAME = 'eth0'


class Logger(object):
    def __init__(self, logfile=''):
        time_struct = time.localtime(time.time())
        log_suffix = time.strftime('real-%Y-%m-%d_%H%M%S.log', time_struct)
        if logfile:
            self.logfile = '%s%s%s' % (BASE_DIR, os.sep, logfile)
        else:
            self.logfile = '%s%s%s' % (BASE_DIR, os.sep, log_suffix)
        # 屏幕对象
        self.logger_c = logging.getLogger('console')
        self.format_c = logging.Formatter('%(message)s')  # 屏幕显示不需要日志格式
        self.stream_c = logging.StreamHandler()
        self.stream_c.setFormatter(self.format_c)
        self.logger_c.setLevel(logging.DEBUG)
        self.logger_c.addHandler(self.stream_c)
        # 日志对象
        self.logger_f = logging.getLogger(log_suffix)
        self.format_f = logging.Formatter('%(message)s')
        self.stream_f = logging.FileHandler(self.logfile)
        self.stream_f.setFormatter(self.format_f)
        self.logger_f.setLevel(logging.DEBUG)
        self.logger_f.addHandler(self.stream_f)
        # 写入日志
        time_struct = time.localtime(time.time())
        msg = time.strftime('%Y-%m-%d_%H:%M:%S', time_struct)
        self.logger_c.info('======== LOG BEGIN %s ========' % msg)
        self.logger_f.info('======== LOG BEGIN %s ========' % msg)

    def set_logfile(self, logfile=None):
        """ 设置自定义文件名日志日志 """
        global BASE_DIR
        if not logfile:
            return
        if logfile:
            self.logfile = '%s%s%s' % (BASE_DIR, os.sep, logfile)
        # 移除文件
        self.logger_f.removeHandler(self.stream_f)
        del self.stream_f
        self.logger_f = logging.getLogger(logfile)
        self.format_f = logging.Formatter('%(message)s')
        self.stream_f = logging.FileHandler(self.logfile)
        self.stream_f.setFormatter(self.format_f)
        self.logger_f.setLevel(logging.DEBUG)
        self.logger_f.addHandler(self.stream_f)
        # 打印初始日志
        time_struct = time.localtime(time.time())
        msg = time.strftime('%Y-%m-%d_%H:%M:%S', time_struct)
        self.logger_c.info('======== LOG BEGIN %s ========' % msg)
        self.logger_f.info('======== LOG BEGIN %s ========' % msg)

    def crate_new_log(self):
        """ 重新生成当前时间的日志 """
        global BASE_DIR
        time_struct = time.localtime(time.time())
        log_suffix = time.strftime('real-%Y-%m-%d_%H%M%S.log', time_struct)
        self.logfile = '%s%s%s' % (BASE_DIR, os.sep, log_suffix)
        self.set_logfile(self.logfile)

    def log(self, msg, print_screen=True):
        """ 打印日志 """
        # 局部变量
        format_color = {0: '%s',  # 默认色
                        1: '\033[32m%s\033[0m',  # 绿色
                        2: '\033[33m%s\033[0m',  # 黄色
                        3: '\033[31m%s\033[0m'  # 红色
                        }
        if not msg:
            return RETURN_FAIL

        self.logger_f.info(msg)
        if print_screen:
            self.logger_c.info(msg)
        return RETURN_OK


class SleepTime(object):
    """    睡眠时钟对象    """
    milli_sec = 0.01
    one_sec = 1
    ten_sec = 10
    one_min = 60
    ten_min = 600
    half_hour = 1800

    def __init__(self):
        pass


def parse_args():
    """
    函数功能：解析参数
    :return: NULL
    """
    global TASK_APP
    global NIC_NAME
    # 获取网卡名称
    logger.log('check eth: begin')
    p = subprocess.Popen('ls /sys/class/net | grep -v lo', shell=True, stdout=subprocess.PIPE)
    nic_list = p.stdout.readlines()
    p.stdout.close()
    # 如果有多张网卡
    if len(nic_list) == 1:
        NIC_NAME = nic_list[0].strip()
    else:
        for nic in nic_list:
            if 'eth' in nic or 'ens' in nic:    # 兼容aws网卡为ens
                NIC_NAME = nic.strip()
                break
    logger.log('found eth: %s' % NIC_NAME)
    # 参数解析
    if len(sys.argv) > 1:
        TASK_APP = sys.argv[1]


class SarType(object):
    rxpps = 'rxpps'
    txpps = 'txpps'
    rxbw = 'rxbw'
    txbw = 'txbw'
    all = 'all'

    def __init__(self):
        pass


class Public(object):
    def __init__(self):
        pass

    @staticmethod
    def create_new_log(prefix=''):
        """
        # 函数功能：创建日志文件
        :param prefix: 日志前缀
        """
        global LOG_FILE
        global BASE_DIR
        base_dir = BASE_DIR
        # 创建log目录
        if not os.path.isdir(base_dir):
            os.mkdir(base_dir)

        time_struct = time.localtime(time.time())
        log_suffix = time.strftime('%Y-%m-%d_%H%M%S.log', time_struct)
        if prefix:
            LOG_FILE = '%s%s%s_%s' % (base_dir, os.path.sep, prefix, log_suffix)
        else:
            LOG_FILE = '%s%s%s' % (base_dir, os.path.sep, log_suffix)

        with open(LOG_FILE, 'a+') as f:
            f.write('======== LOG BEGIN ========' + '\n')
        if DEBUG_MODE:
            logger.log('create_new_log: file=%s' % LOG_FILE)
        return LOG_FILE

    @staticmethod
    def print_log(msg, level=0, log_file='', print_screen=True, new_line=True):
        """    函数功能：打印到日志    """
        # 全局变量
        global logger
        # 局部变量
        format_color = {0: '%s',  # 默认色
                        1: '\033[32m%s\033[0m',  # 绿色
                        2: '\033[33m%s\033[0m',  # 黄色
                        3: '\033[31m%s\033[0m'  # 红色
                        }

        format_msg = format_color[level] % str(msg)
        if log_file:
            stream_file = logging.StreamHandler(log_file)
            stream_file.setLevel(logging.DEBUG)
            format_file = logging.Formatter('%(asctime)s-%(levelname)s:%(message)s')
            stream_file.setFormatter(format_file)
            logger.addHandler(stream_file)
            logger.debug(format_msg)
            logger.removeHandler(stream_file)
            # with open(log_file, 'a+') as f:
            #     if new_line:
            #         f.write(str(msg) + "\n")
            #     else:
            #         f.write(str(msg) + " ")
        if print_screen:
            logger.debug(str(format_msg))
            # if new_line:
            #     print format_msg
            # else:
            #     sys.stdout.write(msg)
            #     sys.stdout.flush()
        return RETURN_OK

    # @staticmethod
    # def copy_ssh_key(host, key_type="password", key_value=''):
    #     """
    #     # 函数功能：建立SSH信任关系
    #     :param host: 目标host
    #     :param key_type:认证类型
    #     :param key_value:秘钥值或者密码值
    #     """
    #     # 局部变量
    #     ssh = None
    #     # 判断本端id_rsa是否存在
    #     if os.path.isfile("/root/.ssh/id_rsa") is False:
    #         ssh = pexpect.spawn("ssh-keygen -t rsa")
    #         ssh.sendline("")
    #         time.sleep(0.2)
    #         ssh.sendline("")
    #         time.sleep(0.2)
    #         ssh.sendline("")
    #         time.sleep(5)
    #         ssh.close()
    #         print "ssh-keygen -t rsa success"
    #
    #     ssh = pexpect.spawn("ssh-copy-id %s" % host)
    #     try:
    #         i = ssh.expect(['password:', 'continue connecting (yes/no)?'], timeout=5)
    #         if i == 0:
    #             ssh.sendline(key_value)
    #             time.sleep(5)
    #         elif i == 1:
    #             ssh.sendline("yes")
    #             ssh.expect("password:")
    #             ssh.sendline(key_value)
    #             time.sleep(5)
    #     except pexpect.EOF:
    #         ssh.close()
    #     except Exception, e:
    #         print "SSH error: %s" % e

    @staticmethod
    def exec_shell_command(host='', cmd_list=None, backgroud=False):
        """
        # 函数功能：在指定主机上运行命令
        :param host: 所在主机，''=本地；返回值0=正常，非零=异常
        :param cmd_list: 命令
        :param backgroud: ssh的时候是否后台执行
        """
        # 局部变量
        ret = RETURN_OK
        tmp_cmd_file = 'tmp-cmd.sh'
        dst_cmd_file = 'run-cmd.sh'

        if len(cmd_list) < 0:
            return RETURN_FAIL
        if DEBUG_MODE:
            logger.log('exec_shell_command: begin, host=%s cmd=%s' % (host, cmd_list))
        # 生成临时命令文件
        with open(tmp_cmd_file, 'w') as f:
            f.writelines([line + ' \n' for line in cmd_list])

        # 文件拷贝,并执行命令
        if host:
            cmd = "script -q -c 'scp %s %s:/root/%s' >/dev/null" % (tmp_cmd_file, host, dst_cmd_file)
            ret = os.system(cmd)
            if backgroud:
                cmd = 'ssh %s sh /root/%s 2>/dev/null 1>/dev/null &' % (host, dst_cmd_file)
            else:
                cmd = 'ssh %s sh /root/%s 2>/dev/null 1>/dev/null' % (host, dst_cmd_file)
            ret = os.system(cmd)
        else:
            cmd = "script -q -c 'cp %s /root/%s' >/dev/null" % (tmp_cmd_file, dst_cmd_file)
            ret = os.system(cmd)
            cmd = 'sh /root/%s 2>/dev/null 1>/dev/null' % dst_cmd_file
            ret = os.system(cmd)

        # 移除临时文件
        os.remove(tmp_cmd_file)
        if DEBUG_MODE:
            logger.log('exec_shell_command: done')
        return ret

    @staticmethod
    def install_software(name_list, host_list):
        """
        # 函数功能：安装软件
        :param name_list: 待安装的软件列表
        :param host_list: 主机列表
        """
        tools_dir = 'tools'
        ret = ''

        soft_list = ['netperf', 'iperf3', 'qperf']
        s_list = list(set(soft_list) & set(name_list))
        ret = s_list
        if len(s_list) == 0:
            return ret

        for s in s_list:
            for host in host_list:
                if s == 'netperf':
                    # 不存在则安装
                    if Public.exec_shell_command('/usr/bin/netperf -V', host) != 0:
                        os.system("script -q -c 'scp %s/netperf %s:/usr/bin/' >/dev/null" % (tools_dir, host))
                        os.system("script -q -c 'scp %s/netserver %s:/usr/bin/' >/dev/null" % (tools_dir, host))
                        Public.exec_shell_command('chmod 777 /usr/bin/netperf', host)
                        Public.exec_shell_command('chmod 777 /usr/bin/netserver', host)
                elif s == 'iperf3':
                    if Public.exec_shell_command('/usr/bin/iperf3 -V', host) != 0:
                        os.system("script -q -c 'scp %s/iperf3 %s:/usr/bin/' >/dev/null" % (tools_dir, host))
                        os.system("script -q -c 'scp %s/libiperf.so.0 %s:/usr/local/lib/' >/dev/null" % (tools_dir, host))
                        Public.exec_shell_command('chmod 777 /usr/bin/iperf3', host)
                elif s == 'qperf':
                    if Public.exec_shell_command('/usr/bin/qperf -V', host) != 0:
                        os.system("script -q -c 'scp %s/qperf %s:/usr/bin/' >/dev/null" % (tools_dir, host))
                        Public.exec_shell_command('chmod 777 /usr/bin/qperf', host)

    @staticmethod
    def start_app_server(name, port_list=None, host_list=None):
        """
        # 函数功能: 启动server进程
        :param name: 程序名称
        :param port_list: 端口列表
        :param host_list: 主机列表
        """
        # 命令列表
        cmd_list = []

        if port_list is None:
            port_list = []
        if host_list is None:
            host_list = []

        name = str(name).lower()
        if name == 'netserver' or name == 'netperf':
            if len(port_list) == 0:
                cmd_list.append('netserver')
            else:
                for port in port_list:
                    cmd_list.append('netserver -p %d' % port)
        elif name == 'iperf3':
            if len(port_list) == 0:
                cmd_list.append('iperf3 -s')
            else:
                for port in port_list:
                    cmd_list.append('iperf3 -s -p %d' % port)
        elif name == 'qperf':
            cmd_list.append('qperf')

        if len(host_list) == 0:  # 本地执行
            for cmd in cmd_list:
                Public.exec_shell_command(cmd)
        else:  # 远程命令
            for host in host_list:
                for cmd in cmd_list:
                    Public.exec_shell_command(cmd, host)

    @staticmethod
    def off(host_list=None, app_list=None):
        """
        # 函数功能：关闭任务
        :param host_list: 主机列表，不写=local
        :param app_list: 程序列表，不写=all
        """
        # 脚本名
        script_name = sys.argv[0]
        # 应用程序列表
        app_list_template = ['netperf', 'netserver', 'iperf', 'iperf3', 'qperf', 'memcached', 'memaslap']
        tmp_cmd_file = 'tmp-cmd.sh'
        dst_cmd_file = 'run-cmd.sh'
        if app_list is None:
            app_list_new = app_list_template
        else:
            app_list_new = app_list

        if host_list is None:
            host_list = []

        if DEBUG_MODE:
            logger.log('off: host=%s app_list=%s' % (str(host_list), str(app_list_new)))
        app_name = '|'.join(app_list_new)
        cmd = "for i in `ps -ef | grep -v grep | grep -E '%s' | grep -v %s | awk '{print $2}'`;" \
              "do kill -9 $i;sleep 0.01;done" % (app_name, script_name)
        with open(tmp_cmd_file, 'w') as f:
            f.write(cmd + '\n')

        # 文件拷贝,并执行命令
        # 远程多主机
        if len(host_list) > 0:
            for host in host_list:
                ret = os.system("script -q -c 'scp %s %s:/root/%s' >/dev/null" % (tmp_cmd_file, host, dst_cmd_file))
                ret = os.system('ssh %s sh /root/%s 2>/dev/null 1>/dev/null' % (host, dst_cmd_file))
                time.sleep(SleepTime.one_sec)
        # 本地执行
        else:
            ret = os.system("script -q -c 'cp %s /root/%s' >/dev/null" % (tmp_cmd_file, dst_cmd_file))
            ret = os.system('sh /root/%s 2>/dev/null 1>/dev/null' % dst_cmd_file)

        # 关闭服务后，等待一段时间
        time.sleep(SleepTime.ten_sec)
        os.remove(tmp_cmd_file)
        if DEBUG_MODE:
            logger.log('off: done')
        return RETURN_OK

    @staticmethod
    def select_flow_from_host(host=''):
        """
        # 函数功能：根据主机CPU数选择流数
        :param host:
        :return:
        """
        cpu_log = '/tmp/cpu.log'
        cpus = 1
        set_flow = 16
        if host:
            cmd = ["lscpu | grep '^CPU(s)' | awk '{print $2}' > %s" % cpu_log]
            if DEBUG_MODE:
                logger.log('select_flow_from_host: host=%s' % host)
            Public.exec_shell_command(host, cmd)
            time.sleep(SleepTime.one_sec)
            os.system("script -q -c 'scp %s:%s %s' >/dev/null" % (host, cpu_log, cpu_log))
            # 如果文件不存在，返回默认流数
            if not os.path.isfile(cpu_log):
                return set_flow

            with open(cpu_log, 'r') as f:
                cpus = int(f.readline())
            # 根据cpu数选流
            cpus_list = []
            for i in FLOW_STEP.keys():
                cpus_list.append(int(i.replace('U', '')))
            # CPU字典从大到小排序
            cpus_list.sort(reverse=True)
            for i in cpus_list:
                # 命中字典位置退出
                if cpus >= i:
                    break
            # 从字典里取流数
            set_flow = FLOW_STEP['%dU' % i]
            if DEBUG_MODE:
                logger.log('select_flow_from_host: flow=%d' % set_flow)
        # 清理临时文件
        os.remove(cpu_log)
        return set_flow


class SarCollector(object):
    """" sar结果采集对象 """
    sar_send = 'send'
    sar_recv = 'recv'
    sar_both = 'both'
    send_sum = 'send_sum'
    recv_sum = 'recv_sum'
    sar_tmp_dir = '/tmp/'
    header_format = '{:<12}  {:<5}  {:<11}  {:<11}  {:<11}  {:<11}'
    sar_format = '{:<12}  {:<5}  {:<11.2f}  {:<11.2f}  {:<11.2f}  {:<11.2f}'

    def __init__(self, src_host=None, dst_host=None, c_time=60, c_type='all',
                 direction='send', details=False, eth=NIC_NAME, sleep_time=30):
        self.src_host = copy.deepcopy(src_host) if src_host else []
        self.dst_host = copy.deepcopy(dst_host) if dst_host else []
        self.c_time = c_time
        self.c_type = c_type
        self.direction = direction
        self.details = details
        self.eth = eth
        self.sleep_time = sleep_time
        self.send_sum = 'send_sum'
        self.recv_sum = 'recv_sum'
        self.data = {}
        self.init_data()
        self.summary = {}

    def init_data(self):
        """ 初始化sar结果 """
        if self.data:
            del self.data
            gc.collect()
        self.data = {self.send_sum: {'sar': [], 'avg': []},
                     self.recv_sum: {'sar': [], 'avg': []}
                     }
        if self.src_host:
            for i in self.src_host:
                self.data[i] = {'sar': [], 'avg': []}
        if self.dst_host:
            for i in self.dst_host:
                self.data[i] = {'sar': [], 'avg': []}
        # 多次测试的结果


    def set_param(self, src_host=None, dst_host=None, c_time=None, c_type=None, direction=None, details=None, eth=None):
        """ 设置sar采集参数 """
        self.src_host = copy.deepcopy(src_host)
        self.dst_host = copy.deepcopy(dst_host)
        if c_time:
            self.c_time = c_time
        if c_type:
            self.c_type = c_type
        if direction:
            self.direction = direction
        if details:
            self.details = details
        if eth:
            self.eth = eth

    def __save_data(self, host, sar_file=None):
        """ 保存一个host的sar """
        if not host or not sar_file:
            logger.log('ERROR: host or sar_file is None')
            return RETURN_FAIL
        # 读取sar文件
        if not os.path.isfile(sar_file):
            return RETURN_FAIL
        with open(sar_file, 'r') as f:
            for line in f:
                if ('Average' in line) and (self.eth in line):  # average
                    ret_list = line.strip().split()
                    ele = [
                           ret_list[0],     # average
                           ret_list[1],     # eth
                           round(float(ret_list[2]), 2),  # rxpps
                           round(float(ret_list[3]), 2),  # txpps
                           round(float(ret_list[4]), 2),  # rxbw
                           round(float(ret_list[5]), 2)]  # txbw
                    if host in self.data.keys():
                        self.data[host]['avg'] = ele      # 修改记录
                    else:
                        self.data[host] = {'sar': [], 'avg': ele}  # 不存在则增加记录
                elif self.eth in line:      # 每秒值
                    ret_list = line.strip().split()
                    ele = [
                           ret_list[0] + ' ' + ret_list[1],  # time
                           ret_list[2],                   # eth
                           round(float(ret_list[3]), 2),  # rxpps
                           round(float(ret_list[4]), 2),  # txpps
                           round(float(ret_list[5]), 2),  # rxbw
                           round(float(ret_list[6]), 2)]  # txbw
                    if host in self.data.keys():
                        self.data[host]['sar'].append(ele)  # 修改记录
                    else:
                        self.data[host] = {'sar': [ele], 'avg': []}  # 不存在则增加记录
        # 删除临时文件
        time.sleep(3)
        logger.log('remove %s' % sar_file)
        os.remove(sar_file)
        return RETURN_OK

    def __calc_sum(self, host_list, sum_type='send_sum'):
        """ 计算所有host的sar平均值 """
        if not host_list:
            return RETURN_FAIL

        sum_rx_pps = 0
        sum_tx_pps = 0
        sum_rx_bw = 0
        sum_tx_bw = 0
        for i in range(0, len(self.data[host_list[0]]['sar'])):
            rx_pps = 0
            tx_pps = 0
            rx_bw = 0
            tx_bw = 0
            for host in host_list:
                rx_pps += self.data[host]['sar'][i][2]
                tx_pps += self.data[host]['sar'][i][3]
                rx_bw += self.data[host]['sar'][i][4]
                tx_bw += self.data[host]['sar'][i][5]
            # 所有host的一行数据
            rx_pps = rx_pps/len(host_list)
            tx_pps = tx_pps/len(host_list)
            rx_bw = rx_bw/len(host_list)
            tx_bw = tx_bw/len(host_list)
            # 所有主机一行的和
            sum_rx_pps += rx_pps
            sum_tx_pps += tx_pps
            sum_rx_bw += rx_bw
            sum_tx_bw += tx_bw
            self.data[sum_type]['sar'].append(['%ds' % (i+1), self.eth, rx_pps, tx_pps, rx_bw, tx_bw])
        # 所有人的平均
        sum_rx_pps = sum_rx_pps/len(self.data[host_list[0]]['sar'])
        sum_tx_pps = sum_tx_pps/len(self.data[host_list[0]]['sar'])
        sum_rx_bw = sum_rx_bw/len(self.data[host_list[0]]['sar'])
        sum_tx_bw = sum_tx_bw/len(self.data[host_list[0]]['sar'])
        self.data[sum_type]['avg'] = [self.data[host_list[0]]['avg'][0],
                                      self.data[host_list[0]]['avg'][1],
                                      sum_rx_pps, sum_tx_pps, sum_rx_bw, sum_tx_bw
                                      ]

    def get_sar_data(self, host_list, sum_type, prefix=''):
        for i in host_list:
            os.system("script -q -c 'scp %s:/root/%s.log %s' >/dev/null" % (i, i, self.sar_tmp_dir))
            if DEBUG_MODE:
                logger.log('host:%s\tsar -n DEV 1 %d' % (i, self.c_time))
            # 打印sar采集标记
            if host_list == self.src_host:
                direction = 'send'
            else:
                direction = 'recv'
            logger.log('sar on %s: %s' % (direction, i))
            self.__save_data(i, '%s%s.log' % (self.sar_tmp_dir, i))
            # 打印数据记录
            # 表头
            msg = self.header_format.format('00:00:00 AM', 'IFACE', 'rxpck/s', 'txpck/s', 'rxkB/s', 'txkB/s')
            logger.log(msg)
            # host明细数据
            for record in self.data[i]['sar']:
                msg = self.sar_format.format(record[0], record[1], record[2], record[3], record[4], record[5])
                logger.log(msg)
            # host average
            msg = self.sar_format.format(self.data[i]['avg'][0],
                                         self.data[i]['avg'][1],
                                         self.data[i]['avg'][2],
                                         self.data[i]['avg'][3],
                                         self.data[i]['avg'][4],
                                         self.data[i]['avg'][5],
                                         )
            logger.log(msg)
        # 所有主机汇总
        self.__calc_sum(host_list, sum_type)
        # 仅当并行打流ECS数量大于1才打印
        if len(host_list) > 1:
            logger.log('sar %s on %s' % (sum_type, str(host_list)))
            # 表头
            msg = self.header_format.format('00:00:00 AM', 'IFACE', 'rxpck/s', 'txpck/s', 'rxkB/s', 'txkB/s')
            logger.log(msg)
            for record in self.data[sum_type]['sar']:
                msg = self.sar_format.format(record[0], record[1], record[2], record[3], record[4], record[5])
                logger.log(msg)
            # 平均
            record = self.data[sum_type]['avg']
            msg = self.sar_format.format(record[0], record[1], record[2], record[3], record[4], record[5])
            logger.log(msg)

    def copy_data(self, send_sum=None, recv_sum=None):
        """ 拷贝汇总数据 """
        if send_sum and self.src_host:
            send_sum['eth'] = self.data['send_sum']['sar'][0][1]
            for record in self.data['send_sum']['sar']:
                send_sum['rxpps'].append(record[2])
                send_sum['txpps'].append(record[3])
                send_sum['rxbw'].append(record[4])
                send_sum['txbw'].append(record[5])
        if recv_sum and self.dst_host:
            recv_sum['eth'] = self.data['recv_sum']['sar'][0][1]
            for record in self.data['recv_sum']['sar']:
                recv_sum['rxpps'].append(record[2])
                recv_sum['txpps'].append(record[3])
                recv_sum['rxbw'].append(record[4])
                recv_sum['txbw'].append(record[5])

    def generate_percentile(self, percent=(1, 5, 10)):
        """ 生成百分比，默认比较1%、5%、10%、90%、95%、99%
        """
        def percentile(data_list, percent):
            if percent < 0.000001:      # 浮点型，不能用==
                return min(data_list)
            elif percent > 0.999999:
                return max(data_list)

            count = len(data_list)
            sum = (count - 1) * percent  # 计算
            pos_i = int(math.floor(sum))
            pos_j = sum - pos_i
            # print 'sum=%f\tpos_i=%d\tpos_j=%f' % (sum, pos_i, pos_j)
            percent_data = (1 - pos_j) * data_list[pos_i] + pos_j * data_list[pos_i + 1]
            return percent_data

            # 计算平均值
            sum = 0
            for i in data_list:
                sum += i
            qos0 = sum / len(data_list)

            # 计算百分位
            qos1_t = get_data(data_list, percent)
            qos2_t = get_data(data_list, 1 - percent)
            if qos1_t < qos2_t:
                qos1 = qos1_t
                qos2 = qos2_t
            else:
                qos1 = qos2_t
                qos2 = qos1_t

            return float('%.2f' % qos0), float('%.2f' % qos1), float('%.2f' % qos2), \
                   float('%.2f' % (100 - qos1 * 100. / qos0)), float('%.2f' % (qos2 * 100. / qos0 - 100))
        pass

    def fetch_data(self):
        # 等待采集结束
        if DEBUG_MODE:
            logger.log('sar: begin fetch_data')
        time.sleep(self.c_time + self.sleep_time + SleepTime.ten_sec)
        # 获取数据
        if self.src_host:
            self.get_sar_data(self.src_host, self.send_sum)
        if self.dst_host:
            self.get_sar_data(self.dst_host, self.recv_sum)
        # 结束
        if DEBUG_MODE:
            logger.log('%s end' % self.__class__.__name__)

    def run(self, sleep_time=30):
        """ sar采集入口
        :param sleep_time: 等待时间，这样可以让sar指令提前运行，避免打流后发送sar指令拥塞
        """
        # 等待时间
        if sleep_time:
            self.sleep_time = sleep_time
        # 初始化数据
        self.init_data()
        if DEBUG_MODE:
            logger.log('%s: begin' % repr(self.__class__.__name__))

        # 参数校验
        if (self.src_host is None) and (self.dst_host is None):
            logger.log('ERROR: src_host and dst_host is None')
            return RETURN_FAIL
        if self.c_type and (self.c_type not in [SarType.rxpps, SarType.txpps, SarType.rxbw, SarType.txbw, SarType.all]):
            logger.log('ERROR: sar_type error')
            return RETURN_FAIL
        if DEBUG_MODE:
            logger.log('sar param:%s' % repr(self.__dict__))
        # 为了保障采集时间一致，不做sleep等待
        if self.src_host:
            for i in self.src_host:
                if sleep_time:
                    cmd = 'sleep %d;sar -n DEV 1 %d > /root/%s.log &' % (sleep_time, self.c_time, i)
                else:
                    cmd = 'sar -n DEV 1 %d > /root/%s.log &' % (self.c_time, i)
                Public.exec_shell_command(i, [cmd], backgroud=True)     # 后台执行，不要阻塞
        if self.dst_host:
            for i in self.dst_host:
                if sleep_time:
                    cmd = 'sleep %d;sar -n DEV 1 %d > /root/%s.log &' % (sleep_time, self.c_time, i)
                else:
                    cmd = 'sar -n DEV 1 %d > /root/%s.log &' % (self.c_time, i)
                Public.exec_shell_command(i, [cmd], backgroud=True)     # 后台执行，不要阻塞

        return RETURN_OK


class TestParam(object):
    """    测试参数类    """
    def __init__(self, src_host=None, dst_host=None, test_type='udp_stream', base_port=7001,
                 flows=16, set_mb='', set_kpps=-1, test_time=3600, pkt_len=64):
        """
        # 测试参数
        :param src_host: 源IP列表
        :param dst_host: 目的IP列表
        :param test_type: 测试类型tcp_stream, iperf3
        :param base_port: 起始端口
        :param flows: 流数
        :param set_mb: 设定的带宽，仅iperf3有效
        :param set_kpps: 设定的PPS，单位K，仅iperf3有效，-1表示未指定
        :param test_time: 测试时长
        :param pkt_len: 包长
        """
        if src_host:
            self.src_host = copy.deepcopy(src_host)
        else:
            self.src_host = []
        if dst_host:
            self.dst_host = copy.deepcopy(dst_host)
        else:
            self.dst_host = []
        self.test_type = test_type
        self.base_port = base_port
        self.flows = flows
        self.set_mb = set_mb
        self.set_kpps = set_kpps
        self.test_time = test_time
        self.pkt_len = pkt_len

    def set_param(self, src_host=None, dst_host=None, test_type=None, base_port=None, flows=None, set_mb=None,
                  set_kpps=None, test_time=None, pkt_len=None):
        """
        # 测试参数
        :param src_host: 源IP列表
        :param dst_host: 目的IP列表
        :param test_type: 测试类型tcp_stream, iperf3
        :param base_port: 起始端口
        :param flows: 流数
        :param set_mb: 设定的带宽，仅iperf3有效
        :param set_kpps: 设定的PPS，单位K，仅iperf3有效
        :param test_time: 测试时长
        :param pkt_len: 包长
        """
        if src_host:
            if type(src_host) is list:
                self.src_host = copy.deepcopy(src_host)
            else:
                self.src_host = copy.deepcopy([src_host])
        if dst_host:
            if type(dst_host) is list:
                self.dst_host = copy.deepcopy(dst_host)
            else:
                self.dst_host = copy.deepcopy([dst_host])
        if test_type:
            self.test_type = test_type
        if base_port:
            self.base_port = base_port
        if flows:
            self.flows = flows
        if set_mb:
            self.set_mb = set_mb
        if set_kpps:
            self.set_kpps = set_kpps
        if test_time:
            self.test_time = test_time
        if pkt_len:
            self.pkt_len = pkt_len
        # 参数冲突处理，如果设置了带宽，则带宽优先
        if self.set_mb:
            self.set_kpps = 0

    @property
    def check_param(self):
        """
        参数有效性校验
        """
        ret = RETURN_OK
        if (self.base_port <= 0) or (self.flows <= 0) or (self.test_time <= 0) or (self.pkt_len <= 0):
            ret = RETURN_FAIL
        return ret


class NetperfTester(object):
    def __init__(self, param=None, sar=None):
        self.param = copy.deepcopy(param) if param else TestParam()
        self.sar = copy.deepcopy(sar) if sar else SarCollector()

    def make_netperf_cmd(self, src_host, dst_host):
        """
        # 函数功能：单向netperf测试命令解析
        """
        # 局部变量：返回结果值，列表成员为字典格式{host='192.168.1.1', cmd = [cmd1,cmd2,cmd3...]}
        client_cmd = []
        server_cmd = []
        test_method_template = ['TCP_STREAM', 'UDP_STREAM', 'TCP_RR', 'UDP_RR', 'TCP_CRR']

        test_type = self.param.test_type.upper()
        if test_type not in test_method_template:
            return RETURN_FAIL, client_cmd, server_cmd
        if len(src_host) == 0 or len(dst_host) == 0:
            return RETURN_FAIL, client_cmd, server_cmd

        port_index = self.param.base_port
        # 初始命令字典
        for i in src_host:
            element = dict(host=i, cmd=[])
            client_cmd.append(element)
        for i in dst_host:
            element = dict(host=i, cmd=[])
            server_cmd.append(element)

        if DEBUG_MODE:
            logger.log('make_netperf_cmd begin')
        # 只适用于1:N  N:1 或者N:N的场景，不支持N:M的复杂场景。
        # N:N
        if len(src_host) == len(dst_host):
            for i in range(0, len(src_host)):
                # 传入flows=0则表示自动判断流数
                if self.param.flows == 0:
                    self.param.flows = Public.select_flow_from_host(src_host[i])

                for j in range(0, self.param.flows):
                    c_cmd = 'netperf -H %s -p %d -t %s -l %d -- -m %d 2>/dev/null 1>/dev/null &' \
                            % (dst_host[i], port_index, test_type, self.param.test_time, self.param.pkt_len)
                    s_cmd = 'netserver -p %d 2>/dev/null 1>/dev/null &' % port_index
                    port_index += 1
                    # 记录命令
                    for ele in client_cmd:
                        if ele['host'] == src_host[i]:
                            ele['cmd'].append(c_cmd)
                            break
                    for ele in server_cmd:
                        if ele['host'] == dst_host[i]:
                            ele['cmd'].append(s_cmd)
                            break
        # 1:N
        elif len(src_host) == 1 and len(dst_host) > 1:
            # 传入flows=0则表示自动判断流数
            if self.param.flows == 0:
                self.param.flows = Public.select_flow_from_host(src_host[0])
            per_flow = self.param.flows / len(dst_host)
            left_flow = self.param.flows % len(dst_host)
            for i in range(0, len(dst_host)):
                for j in range(0, per_flow):
                    c_cmd = 'netperf -H %s -p %d -t %s -l %d -- -m %d 2>/dev/null 1>/dev/null &' \
                            % (dst_host[i], port_index, test_type, self.param.test_time, self.param.pkt_len)
                    s_cmd = 'netserver -p %d 2>/dev/null 1>/dev/null &' % port_index
                    port_index += 1
                    # 记录命令
                    for ele in client_cmd:
                        if ele['host'] == src_host[0]:
                            ele['cmd'].append(c_cmd)
                            break
                    for ele in server_cmd:
                        if ele['host'] == dst_host[i]:
                            ele['cmd'].append(s_cmd)
                            break

            for j in range(0, left_flow):
                c_cmd = 'netperf -H %s -p %d -t %s -l %d -- -m %d 2>/dev/null 1>/dev/null &' \
                        % (dst_host[-1], port_index, test_type, self.param.test_time, self.param.pkt_len)
                s_cmd = 'netserver -p %d 2>/dev/null 1>/dev/null &' % port_index
                port_index += 1
                # 记录命令
                for ele in client_cmd:
                    if ele['host'] == src_host[0]:
                        ele['cmd'].append(c_cmd)
                        break
                for ele in server_cmd:
                    if ele['host'] == dst_host[-1]:
                        ele['cmd'].append(s_cmd)
                        break
        # N:1
        elif len(src_host) > 1 and len(dst_host) == 1:
            if self.param.flows == 0:
                self.param.flows = Public.select_flow_from_host(dst_host[0])
            per_flow = self.param.flows / len(src_host)
            left_flow = self.param.flows % len(src_host)
            for i in range(0, len(src_host)):
                for j in range(0, per_flow):
                    c_cmd = 'netperf -H %s -p %d -t %s -l %d -- -m %d 2>/dev/null 1>/dev/null &' \
                            % (dst_host[0], port_index, test_type, self.param.test_time, self.param.pkt_len)
                    s_cmd = 'netserver -p %d 2>/dev/null 1>/dev/null &' % port_index
                    port_index += 1
                    # 记录命令
                    for ele in client_cmd:
                        if ele['host'] == src_host[i]:
                            ele['cmd'].append(c_cmd)
                            break
                    for ele in server_cmd:
                        if ele['host'] == dst_host[0]:
                            ele['cmd'].append(s_cmd)
                            break

            for j in range(0, left_flow):
                c_cmd = 'netperf -H %s -p %d -t %s -l %d -- -m %d 2>/dev/null 1>/dev/null &' \
                        % (dst_host[-1], port_index, test_type, self.param.test_time, self.param.pkt_len)
                s_cmd = 'netserver -p %d 2>/dev/null 1>/dev/null &' % port_index
                port_index += 1
                # 记录命令
                for ele in client_cmd:
                    if ele['host'] == src_host[-1]:
                        ele['cmd'].append(c_cmd)
                        break
                for ele in server_cmd:
                    if ele['host'] == dst_host[0]:
                        ele['cmd'].append(s_cmd)
                        break
        # N:M复杂场景，不支持
        else:
            return RETURN_FAIL, client_cmd, server_cmd

        if DEBUG_MODE:
            logger.log('make_netperf_cmd end')
        return RETURN_OK, client_cmd, server_cmd

    def stop(self):
        """ 停止测试 """
        Public.off(self.param.src_host + self.param.dst_host, ['netperf', 'netserver'])

    def run(self, prefix=''):
        """    功能，运行netperf命令    """
        r, c, s = self.make_netperf_cmd(self.param.src_host, self.param.dst_host)
        if DEBUG_MODE:
            logger.log('NetperfTester run: src=%s  dst=%s' % (str(self.param.src_host), str(self.param.dst_host)))
            logger.log('test.param=%s' % repr(self.param.__dict__))
        if r == RETURN_FAIL:
            return RETURN_FAIL
        # 停止要打的流
        self.stop()
        if DEBUG_MODE:
            logger.log('call_netperf: start server')
        # 打印信息
        logger.log('%snetperf: %s --> %s type=%s pkt_len=%d' %
                   (prefix, self.param.src_host, self.param.dst_host, self.param.test_type, self.param.pkt_len))
        # 启动server
        for i in s:
            Public.exec_shell_command(i['host'], i['cmd'])
            time.sleep(SleepTime.milli_sec)
        time.sleep(SleepTime.ten_sec)
        # 启动client
        if DEBUG_MODE:
            logger.log('call_netperf: start client')
        for i in c:
            Public.exec_shell_command(i['host'], i['cmd'])
            time.sleep(SleepTime.milli_sec)
        if DEBUG_MODE:
            logger.log('NetperfTester run: done')

class Iperf3Tester(object):
    def __init__(self, param=None, sar=None):
        self.param = copy.deepcopy(param) if param else TestParam()
        self.sar = copy.deepcopy(sar) if sar else SarCollector()

    def select_iperf3_bw_from_flow(self):
        """
        # 函数功能：根据流数和包长计算iperf3 带宽
        """
        ret_bw = self.param.set_mb
        if (self.param.set_kpps > 0) and (self.param.flows > 0) and (self.param.pkt_len > 0):
            ret_bw = '%sM' % str(round(self.param.set_kpps*1000.0*self.param.pkt_len*8/self.param.flows/1000/1000, 3))
        return ret_bw

    def make_iperf3_cmd(self):
        """
        # 函数功能：单向iperf3测试命令解析
        """
        # 局部变量：返回结果值，列表成员为字典格式{host='192.168.1.1', cmd = [cmd1,cmd2,cmd3...]}
        client_cmd = []
        server_cmd = []
        test_method_template = ['TCP', 'UDP']

        test_type = self.param.test_type.upper()
        if test_type not in test_method_template:
            return RETURN_FAIL, client_cmd, server_cmd
        if len(self.param.src_host) == 0 or len(self.param.dst_host) == 0:
            return RETURN_FAIL, client_cmd, server_cmd

        port_index = self.param.base_port
        # 初始命令字典
        for i in self.param.src_host:
            element = dict(host=i, cmd=[])
            client_cmd.append(element)
        for i in self.param.dst_host:
            element = dict(host=i, cmd=[])
            server_cmd.append(element)

        # 只适用于1:N  N:1 或者N:N的场景，不支持N:M的复杂场景。
        # N:N
        if len(self.param.src_host) == len(self.param.dst_host):
            # 传入flows=0则表示自动判断流数
            for i in range(0, len(self.param.src_host)):
                if self.param.flows == 0:
                    self.param.flows = Public.select_flow_from_host(self.param.src_host[i])
                # 根据PPS选择带宽
                if self.param.set_kpps:
                    self.param.set_mb = self.select_iperf3_bw_from_flow()
                if DEBUG_MODE:
                    logger.log('make_iperf3_cmd: self.param=%s' % repr(self.param.__dict__))
                logger.log('host=%s\tflows=%d' % (self.param.src_host[i], self.param.flows))
                for j in range(0, self.param.flows):
                    if test_type == 'TCP':
                        if self.param.pkt_len:
                            c_cmd = 'iperf3 -c %s -p %d -b %s -t %d -l %d 2>/dev/null 1>/dev/null &' \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb,
                                       self.param.test_time, self.param.pkt_len)
                        else:
                            c_cmd = 'iperf3 -c %s -p %d -b %s -t %d 2>/dev/null 1>/dev/null &' \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb, self.param.test_time)
                    else:
                        if self.param.pkt_len:
                            c_cmd = 'iperf3 -c %s -p %d -u -b %s -t %d -l %d 2>/dev/null 1>/dev/null &' \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb,
                                       self.param.test_time, self.param.pkt_len)
                        else:
                            c_cmd = 'iperf3 -c %s -p %d -u -b %s -t %d 2>/dev/null 1>/dev/null &' \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb, self.param.test_time)

                    s_cmd = 'iperf3 -s -p %d 2>/dev/null 1>/dev/null &' % port_index
                    port_index += 1
                    # 记录命令
                    for ele in client_cmd:
                        if ele['host'] == self.param.src_host[i]:
                            ele['cmd'].append(c_cmd)
                            break
                    for ele in server_cmd:
                        if ele['host'] == self.param.dst_host[i]:
                            ele['cmd'].append(s_cmd)
                            break
        # 1:N
        elif len(self.param.src_host) == 1 and len(self.param.dst_host) > 1:
            # 传入flows=0则表示自动判断流数
            if self.param.flows == 0:
                self.param.flows = Public.select_flow_from_host(self.param.src_host[0])
            # 带宽计算
            self.param.set_mb = self.select_iperf3_bw_from_flow()
            if DEBUG_MODE:
                logger.log('make_iperf3_cmd: self.param=%s' % repr(self.param.__dict__))
            logger.log('host=%s\tflows=%d' % (self.param.src_host[0], self.param.flows))
            per_flow = self.param.flows / len(self.param.dst_host)
            left_flow = self.param.flows % len(self.param.dst_host)
            for i in range(0, len(self.param.dst_host)):
                for j in range(0, per_flow):
                    if test_type == 'TCP':
                        if self.param.pkt_len:
                            c_cmd = "iperf3 -c %s -p %d -b %s -t %d -l %d 2>/dev/null 1>/dev/null &" \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb,
                                       self.param.test_time, self.param.pkt_len)
                        else:
                            c_cmd = "iperf3 -c %s -p %d -b %s -t %d 2>/dev/null 1>/dev/null &" \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb, self.param.test_time)
                    else:
                        if self.param.pkt_len:
                            c_cmd = "iperf3 -c %s -p %d -u -b %s -t %d -l %d 2>/dev/null 1>/dev/null &" \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb,
                                       self.param.test_time, self.param.pkt_len)
                        else:
                            c_cmd = "iperf3 -c %s -p %d -u -b %s -t %d 2>/dev/null 1>/dev/null &" \
                                    % (self.param.dst_host[i], port_index, self.param.set_mb, self.param.test_time)

                    s_cmd = 'iperf3 -s -p %d 2>/dev/null 1>/dev/null &' % port_index
                    port_index += 1
                    # 记录命令
                    for ele in client_cmd:
                        if ele['host'] == self.param.src_host[0]:
                            ele['cmd'].append(c_cmd)
                            break
                    for ele in server_cmd:
                        if ele['host'] == self.param.dst_host[i]:
                            ele['cmd'].append(s_cmd)
                            break

            for j in range(0, left_flow):
                if test_type == 'TCP':
                    if self.param.pkt_len:
                        c_cmd = "iperf3 -c %s -p %d -b %s -t %d -l %d 2>/dev/null 1>/dev/null &" \
                                % (self.param.dst_host[-1], port_index, self.param.set_mb,
                                   self.param.test_time, self.param.pkt_len)
                    else:
                        c_cmd = "iperf3 -c %s -p %d -b %s -t %d -l %d 2>/dev/null 1>/dev/null &" \
                                % (self.param.dst_host[-1], port_index, self.param.set_mb,
                                   self.param.test_time, self.param.pkt_len)
                else:
                    if self.param.pkt_len:
                        c_cmd = "iperf3 -c %s -p %d -u -b %s -t %d -l %d 2>/dev/null 1>/dev/null &" \
                                % (self.param.dst_host[-1], port_index, self.param.set_mb,
                                   self.param.test_time, self.param.pkt_len)
                    else:
                        c_cmd = "iperf3 -c %s -p %d -u -b %s -t %d 2>/dev/null 1>/dev/null &" \
                                % (self.param.dst_host[-1], port_index, self.param.set_mb, self.param.test_time)

                s_cmd = 'iperf3 -s -p %d 2>/dev/null 1>/dev/null &' % port_index
                port_index += 1
                # 记录命令
                for ele in client_cmd:
                    if ele['host'] == self.param.src_host[0]:
                        ele['cmd'].append(c_cmd)
                        break
                for ele in server_cmd:
                    if ele['host'] == self.param.dst_host[-1]:
                        ele['cmd'].append(s_cmd)
                        break
        # N:1
        elif len(self.param.src_host) > 1 and len(self.param.dst_host) == 1:
            # 传入flows=0则表示自动判断流数
            if self.param.flows == 0:
                self.param.flows = Public.select_flow_from_host(self.param.dst_host[0])
            # 带宽计算
            self.param.set_mb = self.select_iperf3_bw_from_flow()
            if DEBUG_MODE:
                logger.log('make_iperf3_cmd: self.param=%s' % repr(self.param.__dict__))
            logger.log('host=%s\tflows=%d' % (self.param.dst_host[0], self.param.flows))
            per_flow = self.param.flows / len(self.param.src_host)
            left_flow = self.param.flows % len(self.param.src_host)
            for i in range(0, len(self.param.src_host)):
                for j in range(0, per_flow):
                    if test_type == 'TCP':
                        c_cmd = "iperf3 -c %s -p %d -b %s -t %s -l %d 2>/dev/null 1>/dev/null &" \
                                % (self.param.dst_host[0], port_index, self.param.set_mb,
                                   self.param.test_time, self.param.pkt_len)
                    else:
                        c_cmd = "iperf3 -c %s -p %d -u -b %s -t %s -l %d 2>/dev/null 1>/dev/null &" \
                                % (self.param.dst_host[0], port_index, self.param.set_mb,
                                   self.param.test_time, self.param.pkt_len)

                    s_cmd = 'iperf3 -s -p %d 2>/dev/null 1>/dev/null &' % port_index
                    port_index += 1
                    # 记录命令
                    for ele in client_cmd:
                        if ele['host'] == self.param.src_host[i]:
                            ele['cmd'].append(c_cmd)
                            break
                    for ele in server_cmd:
                        if ele['host'] == self.param.dst_host[0]:
                            ele['cmd'].append(s_cmd)
                            break

            for j in range(0, left_flow):
                if test_type == 'TCP':
                    c_cmd = "iperf3 -c %s -p %d -b %s -t %s -l %d 2>/dev/null 1>/dev/null &" \
                            % (self.param.dst_host[-1], port_index, self.param.set_mb,
                               self.param.test_time, self.param.pkt_len)
                else:
                    c_cmd = "iperf3 -c %s -p %d -u -b %s -t %s -l %d 2>/dev/null 1>/dev/null &" \
                            % (self.param.dst_host[-1], port_index, self.param.set_mb,
                               self.param.test_time, self.param.pkt_len)

                s_cmd = 'iperf3 -s -p %d 2>/dev/null 1>/dev/null &' % port_index
                port_index += 1
                # 记录命令
                for ele in client_cmd:
                    if ele['host'] == self.param.src_host[-1]:
                        ele['cmd'].append(c_cmd)
                        break
                for ele in server_cmd:
                    if ele['host'] == self.param.dst_host[0]:
                        ele['cmd'].append(s_cmd)
                        break
            pass
        # N:M复杂场景，不支持
        else:
            return RETURN_FAIL, client_cmd, server_cmd
        return RETURN_OK, client_cmd, server_cmd

    def call_iperf3(self):
        r, c, s = self.make_iperf3_cmd()
        if DEBUG_MODE:
            logger.log('call_iperf3: src=%s  dst=%s' % (str(self.param.src_host), str(self.param.dst_host)))
        if r == RETURN_FAIL:
            return RETURN_FAIL
        # 停止要打的流
        Public.off(self.param.src_host + self.param.dst_host)
        if DEBUG_MODE:
            logger.log('call_iperf3: start server')
        # 启动server
        for i in s:
            Public.exec_shell_command(i['host'], i['cmd'])
            time.sleep(SleepTime.milli_sec)
        time.sleep(SleepTime.ten_sec)
        # 启动client
        if DEBUG_MODE:
            logger.log('call_iperf3: start client')
        for i in c:
            Public.exec_shell_command(i['host'], i['cmd'])
            time.sleep(SleepTime.milli_sec)

    def get_data(self):
        pass

    def run(self):
        """
        # 功能，运行iperf3命令
        """
        Public.off(self.param.src_host + self.param.dst_host)
        msg = ''
        if self.param.set_kpps:
            msg = 'run iperf3, src=%s, dst=%s, type=%s, flow=%d, set_kpps=%d, pktlen=%d' % \
                  (self.param.src_host, self.param.dst_host, self.param.test_type, self.param.flows,
                   self.param.set_kpps, self.param.pkt_len)
        else:
            msg = 'run iperf3, src=%s, dst=%s, type=%s, flow=%d, pktlen=%d' % \
                  (self.param.src_host, self.param.dst_host, self.param.test_type, self.param.flows, self.param.pkt_len)
        logger.log(msg)
        self.call_iperf3()


class QperfTester(object):
    def __init__(self, param=None):
        if param:
            self.param = copy.deepcopy(param)
        else:
            self.param = TestParam()
        # 初始化数据存储
        self.init_data()

    def init_data(self):
        self.data = {'type': self.param.test_type, 'pkt_len': self.param.pkt_len, 'unit': 'us', 'lat': []}

    def make_qperf_cmd(self, src_host, dst_host):
        """
        # 函数功能：qperf命令生成器
        :return:
        """
        client_cmd = []
        server_cmd = []
        test_method_template = ['udp_lat', 'tcp_lat']
        test_type = self.param.test_type.lower()
        if DEBUG_MODE:
            logger.log('%s: begin' % sys._getframe().f_code.co_name)
        if DEBUG_MODE:
            logger.log('%s: src=%s  dst=%s  type=%s  time=%d  pkt_len=%d'
                      % (sys._getframe().f_code.co_name, str(src_host), str(dst_host),
                         self.param.test_type, self.param.test_time, self.param.pkt_len))
        if test_type not in test_method_template:  # 测试方法为止
            return RETURN_FAIL, client_cmd, server_cmd
        if len(src_host) == 0 or len(dst_host) == 0:  # 有一方为0
            return RETURN_FAIL, client_cmd, server_cmd
        if len(src_host) != len(dst_host):  # src与dst个数不等，不支持
            return RETURN_FAIL, client_cmd, server_cmd
        # 参数检查通过,初始命令字典
        for i in src_host:
            element = dict(host=i, cmd=[])
            client_cmd.append(element)
        for i in dst_host:
            element = dict(host=i, cmd=[])
            server_cmd.append(element)
        for i in range(0, len(src_host)):
            c_cmd = 'qperf %s -t %d -m %d -vu %s > /root/%s-qperf.log &' \
                    % (dst_host[i], self.param.test_time, self.param.pkt_len,
                       self.param.test_type, src_host[i])
            s_cmd = 'qperf &'
            # 记录命令
            for ele in client_cmd:
                if ele['host'] == src_host[i]:
                    ele['cmd'].append(c_cmd)
                    break
            for ele in server_cmd:
                if ele['host'] == dst_host[i]:
                    ele['cmd'].append(s_cmd)
                    break
        if DEBUG_MODE:
            logger.log('%s: done' % sys._getframe().f_code.co_name)
        return RETURN_OK, client_cmd, server_cmd

    def call_qperf(self, src_host, dst_host):
        r, c, s = self.make_qperf_cmd(src_host, dst_host)
        if DEBUG_MODE:
            logger.log('src=%s  dst=%s' % (str(src_host), str(dst_host)))
        if r == RETURN_FAIL:
            return RETURN_FAIL
        # 停止qperf
        Public.off(src_host + dst_host, ['qperf'])
        # 启动server
        for i in s:
            if DEBUG_MODE:
                logger.log('call_qperf: host=%s  cmd=%s' % (i['host'], str(i['cmd'])))
            Public.exec_shell_command(i['host'], i['cmd'], backgroud=True)
            time.sleep(SleepTime.milli_sec)
        time.sleep(SleepTime.ten_sec)
        # 启动client
        if DEBUG_MODE:
            logger.log('call_qperf: begin start client')
        for i in c:
            if DEBUG_MODE:
                logger.log('call_qperf: host=%s  cmd=%s' % (i['host'], str(i['cmd'])))
            Public.exec_shell_command(i['host'], i['cmd'])
            time.sleep(SleepTime.milli_sec)

    def fetch_data(self):
        # 采集数据
        time.sleep(SleepTime.one_min + self.param.test_time)
        dst_dir = '/tmp/'
        dst_file = '%s%s-qperf.log' % (dst_dir, self.param.src_host[0])
        if DEBUG_MODE:
            logger.log('call_qperf: begin collect data')
            logger.log('%s%s-qperf.log' % (dst_dir, self.param.src_host[0]))
        os.system("script -q -c 'scp %s:/root/%s-qperf.log %s' >/dev/null" %
                  (self.param.src_host[0], self.param.src_host[0], dst_dir))
        # 如果目标文件不存在，退出
        if not os.path.isfile(dst_file):
            return RETURN_FAIL
        with open(dst_file, 'r') as f:
            lat = 0
            unit = 'us'
            for line in f:
                line = line.strip()
                logger.log(line)
                if 'latency' in line:
                    lat_str = line.split()
                    lat = round(float(lat_str[2]), 1)
                    unit = lat_str[3]
            if 'ms' in unit.lower():
                lat = lat * 1000.
            elif 'sec' in unit.lower():
                lat = lat * 1000. * 1000.
            # 存储数据
            self.data['lat'].append(lat)
            # 清除临时文件
            os.remove(dst_file)

    def run(self, prefix=''):
        """
        # 函数功能：测试qperf延迟
        """
        self.init_data()
        # 执行入口代码
        logger.log('%sqperf: src=%s dst=%s type=%s pkt_len=%d' %
                   (prefix, self.param.src_host[0], self.param.dst_host[0], self.param.test_type, self.param.pkt_len))
        Public.off(self.param.src_host + self.param.dst_host, ['qperf'])
        self.call_qperf(self.param.src_host, self.param.dst_host)


class PingTester(object):
    """ ping测试对象 """
    ping_tmp_dir = '/tmp/'

    def __init__(self, src=None, dst=None, count=60, interval=1.0):
        self.src = src
        self.dst = dst
        self.count = count
        self.interval = interval
        self.data = []
        self.init_data()

    def init_data(self):
        self.data = []

    def _make_cmd(self):
        c_cmd = ['ping %s -c %d -i %i > /root/%s_ping.log &' % (self.dst, self.count, self.interval, self.src)]
        return RETURN_OK, c_cmd, None

    def fetch_data(self):
        # 等待采集结束
        time.sleep(SleepTime.ten_sec + int(self.count*self.interval))
        logger.log('ping: fetch_data')
        cmd = "script -q -c 'scp %s:/root/%s_ping.log %s' > /dev/null" % (self.src, self.src, self.ping_tmp_dir)
        if DEBUG_MODE:
            logger.log(cmd)
        os.system(cmd)
        # 分析数据
        dst_file = '%s%s_ping.log' % (self.ping_tmp_dir, self.src)
        if not os.path.isfile(dst_file):
            return RETURN_FAIL
        with open(dst_file, 'r') as f:
            count = 0
            for line in f:
                line = line.strip()
                # 匹配
                ret = re.search('icmp_seq=\d+[\w\W]*time=[\w\W]*', line)
                if ret:
                    count += 1
                    ret_str = re.split("[ =]", ret.group())
                    try:
                        unit = ret_str[6]
                        lat = round(float(ret_str[5]), 3)
                    except ValueError as e:
                        lat = 0.0
                    except Exception as e:
                        lat = 0.0
                    self.data.append(lat)
        # 移除临时文件
        os.remove(dst_file)

    def run(self, prefix=''):
        logger.log('%sping: start %s to %s' % (prefix, self.src, self.dst))
        self.init_data()
        self._make_cmd()
        r,c,s = self._make_cmd()
        if r == RETURN_FAIL: return RETURN_FAIL
        # 执行测试
        Public.exec_shell_command(self.src, c)


class MemcachedTester(object):
    """ 新浪memcached业务测试 """
    srv_file = '/root/%s_memcached.log'
    tmp_file = '/tmp/%s_memcached.log'
    def __init__(self, src_host=None, dst_host=None, port=22122, t_time=60, thread=16, vusers=256, t_byte=100):
        if src_host:
            self.src_host = src_host if type(src_host) is list else [src_host]
        if dst_host:
            self.dst_host = dst_host if type(dst_host) is list else [dst_host]
        self.port = port
        self.t_time = t_time
        self.thread = thread
        self.vusers = vusers
        self.t_byte = t_byte
        self.data = {}
        self.init_data()

    def init_data(self):
        self.data = {}

    def stop(self):
        Public.off(self.src_host+self.dst_host, ['memcached', 'memaslap'])

    def _make_cmd(self):
        """ 产生memcached测试命令 """
        client_cmd = []
        server_cmd = []
        # 初始命令字典
        for i in self.src_host:
            element = dict(host=i, cmd=[])
            client_cmd.append(element)
        for i in self.dst_host:
            element = dict(host=i, cmd=[])
            server_cmd.append(element)
        if DEBUG_MODE:
            logger.log('make_memcached_cmd begin')
        if len(self.src_host) != len(self.dst_host):
            logger.log('memcached error: len(src_host) != len(dst_host)')
            return RETURN_FAIL
        for client,server in zip(self.src_host, self.dst_host):
            c_cmd = 'memaslap -s %s:%s -t %ds -T %d -c %d -X %dB > %s &' %\
                    (server, self.port, self.t_time, self.thread, self.vusers, self.t_byte, self.srv_file % client)
            s_cmd = 'memcached -p %d -d -u root' % self.port
            # 记录命令
            for ele in client_cmd:
                if ele['host'] == client:
                    ele['cmd'].append(c_cmd)
                    break
            for ele in server_cmd:
                if ele['host'] == server:
                    ele['cmd'].append(s_cmd)
                    break
        # 返回命令结果
        return RETURN_OK, client_cmd, server_cmd

    def fetch_data(self):
        time.sleep(SleepTime.ten_sec + self.t_time)
        logger.log('%s fetch_data begin' % self.__class__.__name__)
        # 拉取结果
        for host in self.src_host:
            cmd = "script -q -c 'scp %s:%s %s' > /dev/null" % (host, self.srv_file % host, self.tmp_file % host)
            os.system(cmd)
        # 分析数据
        for host in self.src_host:
            if not os.path.isfile(self.tmp_file % host):
                return RETURN_FAIL
            tps = 0
            with open(self.tmp_file % host, 'r') as f:
                for line in f:
                    line = line.strip()
                    # 写入日志
                    logger.log(line)
                    if 'TPS' in line:
                        ret_str = re.findall('TPS\W+\d+', line)[0].split(':')
                        try:
                            tps = int(ret_str[1].strip())
                        except Exception as e:
                            logger.log('tps value get error')
                            tps = 0
            # 加入数据仓库
            self.data[host] = tps
            # 清理临时文件
            os.remove(self.tmp_file % host)

    def run(self, prefix=''):
        r,c,s = self._make_cmd()
        if r == RETURN_FAIL:
            return RETURN_FAIL
        # 停止打流
        self.stop()
        logger.log('%sMemcachedTester run: %s --> %s' % (prefix, self.src_host, self.dst_host))
        for i in s:
            Public.exec_shell_command(i['host'], i['cmd'])
            time.sleep(SleepTime.milli_sec)
        time.sleep(SleepTime.ten_sec)
        for i in c:
            Public.exec_shell_command(i['host'], i['cmd'])
            time.sleep(SleepTime.milli_sec)
        if DEBUG_MODE:
            logger.log('MemcachedTester run: done')

def run_ssh_login_and_get_time(src_host_list=None, dst_host_list=None, test_time=100, sleep_gap=2,
                         test_order=ORDER_ALL, test_round=5):
    """
    # 函数功能：测试ssh时长
    :param src_host_list: 源IP列表
    :param dst_host_list: 目的IP列表
    :param test_time: 测试多少次
    :param sleep_gap: ssh等待
    :param test_order: 测试顺序ORDER_ALL=并行   ORDER_STEP=串行
    :param test_round: 循环次数
    """
    def call_ssh(src_host_list, dst_host_list):
        client_cmd = []
        ssh_avg_list = {}  # 数据格式{ '192.168.0.1':{'sum':0, 'avg':0, 'details':[1, 2, 3]} }
        if DEBUG_MODE:
            logger.log('call_ssh: begin make commands')
        for i in src_host_list:
            element = dict(host=i, cmd=[], file='')
            client_cmd.append(element)
            ssh_avg_list[i] = dict(sum=0, avg=0, details=[])
        # 构造命令
        for ip_pair in zip(src_host_list, dst_host_list):
            for ele in client_cmd:
                if ele['host'] == ip_pair[0]:
                    ele['file'] = '/tmp/date_%s' % ele['host']
                    ele['cmd'].append('date +%%s.%%N > %s' % ele['file'])
                    ele['cmd'].append('ssh -o ServerAliveInterval=60 %s echo 2>/dev/null 1>/dev/null' % ip_pair[1])
                    ele['cmd'].append('date +%%s.%%N >> %s' % ele['file'])
                    break
        # 启动client
        for round_num in range(0, test_round):
            if DEBUG_MODE:
                logger.log('call_ssh: start client ssh')
            for tt in range(0, test_time):
                for i in client_cmd:
                    Public.exec_shell_command(i['host'], i['cmd'])
                # 搜集结果
                for i in client_cmd:
                    host = i['host']
                    os.system("script -q -c 'scp %s:%s %s' >/dev/null" % (host, i['file'], i['file']))
                    # os.system('cat %s' % i['file'])
                    with open(i['file'], 'r') as f:
                        time1 = float(f.readline().strip())
                        time2 = float(f.readline().strip())
                        diff_time = round(time2 - time1, 3)
                        ssh_avg_list[host]['sum'] += diff_time
                        ssh_avg_list[host]['details'].append(diff_time)
                        ssh_avg_list[host]['avg'] = ssh_avg_list[host]['sum']/len(ssh_avg_list[host]['details'])
                        logger.log('time=%.3f' % ssh_avg_list[host]['details'][-1])
                time.sleep(sleep_gap)
            # 打印平均
            for i in client_cmd:
                host = i['host']
                logger.log('avg_time=%.3f' % ssh_avg_list[host]['avg'])

            # 每个回合休息一段时间
            if round_num < test_round:
                time.sleep(SleepTime.one_min)

    # 只支持N:N
    if len(src_host_list) != len(dst_host_list):
        return RETURN_FAIL

    # 并行测试
    if test_order == ORDER_ALL:
        call_ssh(src_host_list, dst_host_list)
    # 串行测试
    else:
        for c,s in zip(src_host_list, dst_host_list):
            call_ssh([c], [s])


def run_netperf_task(tester, repeat=1):
    """
    函数功能：netperf业务测试
    :param tester: NetperfTester实例
    :param repeat: 重复几次
    """
    send_dict = {'eth': NIC_NAME, 'rxpps': [], 'txpps': [], 'rxbw': [], 'txbw': []}
    recv_dict = {'eth': NIC_NAME, 'rxpps': [], 'txpps': [], 'rxbw': [], 'txbw': []}
    # 测试次数
    for i in range(0, repeat):
        tester.run('Round %d:    ' % (i+1))
        tester.sar.run(sleep_time=30)
        tester.sar.fetch_data()
        # 拷贝数据
        tester.sar.copy_data(send_dict, recv_dict)
        if i < repeat-1:
            time.sleep(SleepTime.ten_sec)
    # 打印汇总结果
    if len(tester.param.src_host) > 1:
        logger.log('\n=========================== send summary result ===========================')
        for index in range(0, len(send_dict['rxpps'])):
            eth = send_dict['eth']
            rxpps = send_dict['rxpps'][index]
            txpps = send_dict['txpps'][index]
            rxbw = send_dict['rxbw'][index]
            txbw = send_dict['txbw'][index]
            msg = tester.sar.sar_format.format('%ds' % (index+1), eth, rxpps, txpps, rxbw, txbw)
            logger.log(msg)
    if len(tester.param.dst_host) > 1:
        logger.log('\n=========================== recv summary result ===========================')
        for index in range(0, len(recv_dict['rxpps'])):
            eth = recv_dict['eth']
            rxpps = recv_dict['rxpps'][index]
            txpps = recv_dict['txpps'][index]
            rxbw = recv_dict['rxbw'][index]
            txbw = recv_dict['txbw'][index]
            msg = tester.sar.sar_format.format('%ds' % (index+1), eth, rxpps, txpps, rxbw, txbw)
            logger.log(msg)


def run_ping_task(tester, repeat=1):
    """
    函数功能：ping业务测试
    :param tester: PingTester实例
    :param repeat: 重复几次
    """
    for i in range(0, repeat):
        tester.run(prefix='\nRound %d    ' % (i+1))
        tester.fetch_data()
        # 打印结果
        for j in tester.data:
            logger.log(j)
        # 多次测试等待
        if i < repeat-1:
            time.sleep(SleepTime.ten_sec)


def run_qperf_task(tester, repeat=1):
    """
    函数功能：qperf业务测试
    :param tester: QperfTester实例
    :param repeat: 重复几次
    """
    for i in range(0, repeat):
        tester.run(prefix='\nRound %d    ' % (i+1))
        tester.fetch_data()
        # 多次测试等待
        if i < repeat-1:
            time.sleep(SleepTime.ten_sec)


def run_memcached_task(tester, repeat=1):
    for i in range(0, repeat):
        tester.run(prefix='\nRound %d    ' % (i + 1))
        tester.fetch_data()
        # 多次测试等待
        if i < repeat-1:
            time.sleep(SleepTime.ten_sec)


def shutoff_ecs(hosts=None):
    """
    函数功能：关机脚本
    :param hosts:
    :return:
    """
    if hosts:
        if type(hosts) is str:
            hosts = [hosts]
    else:
        return RETURN_FAIL
    # 关机程序
    for host in hosts:
        Public.exec_shell_command(host, ['poweroff'])
        time.sleep(SleepTime.one_sec)


def main():
    # 主函数
    global DEBUG_MODE
    global logger
    # task_app = ['memcached', 'qperf', 'ping', 'netperf']
    task_app = ['netperf']
    test_order = ORDER_ALL
    repeat = 5

    # 获取参数
    if TASK_APP and (TASK_APP not in task_app):
        task_app.append(TASK_APP)
    # 获取IP地址
    src_host_list = re.split("[ ;,]", SRC_HOST)
    dst_host_list = re.split("[ ;,]", DST_HOST)
    # 去列表空格元素
    for i in range(len(src_host_list)-1, 0, -1):
        if not src_host_list[i]:
            src_host_list.pop(i)
    for i in range(len(dst_host_list)-1, 0, -1):
        if not dst_host_list[i]:
            dst_host_list.pop(i)

    # 停止打流
    Public.off(src_host_list + dst_host_list)

    # 打流方式
    if DEBUG_MODE:
        logger.log('main: test_type = %s' % task_app)
    if 'netperf' in task_app:
        netperf_param1 = TestParam(None, None, 'TCP_STREAM', 7001, 0, '0', 0, 7200, 1440)
        netperf_param1.set_param(src_host=src_host_list, dst_host=dst_host_list)
        netperf_tester1 = NetperfTester(netperf_param1)
        netperf_tester1.sar.set_param(src_host=src_host_list, dst_host=None, c_time=60, details=True, eth=NIC_NAME)
        run_netperf_task(netperf_tester1, repeat)
        netperf_tester1.stop()
    if 'iperf3' in task_app:
        # 先测一波梯度pps
        for pps in range(1, 10, 1):
            iperf3_param1 = TestParam(None, None, 'udp', 8001, 0, '', set_kpps=pps, test_time=3600, pkt_len=64)
            iperf3_param1.set_param(src_host=src_host_list, dst_host=dst_host_list, test_time=3600)
            iperf3_test1 = Iperf3Tester(iperf3_param1)
            iperf3_test1.sar.set_param(src_host=src_host_list, c_time=10, details=True, eth=NIC_NAME)
            logger.log()
            iperf3_test1.run()
            iperf3_test1.sar.run()
    if 'qperf' in task_app:
        qperf_test1 = QperfTester()
        qperf_test1.param.set_param([src_host_list[0]], [dst_host_list[0]], 'udp_lat', test_time=60, pkt_len=64)
        run_qperf_task(qperf_test1, repeat)
    if 'ssh' in task_app:
        run_ssh_login_and_get_time([OB_HOST], src_host_list, test_time=100, sleep_gap=2, test_round=5)
    if 'ping' in task_app:
        ping_tester1 = PingTester(src=src_host_list[0], dst=dst_host_list[0], count=3600, interval=1.0)
        run_ping_task(ping_tester1, 1)
    if 'memcached' in task_app:
        memcached_tester1 = MemcachedTester(src_host_list, dst_host_list, 22122, 60, 16, 256, 100)
        run_memcached_task(memcached_tester1, repeat)


if __name__ == '__main__':
    # 创建log目录
    if not os.path.isdir(BASE_DIR):
        os.mkdir(BASE_DIR)
    # 创建日志对象
    logger = Logger()
    # 解析参数
    parse_args()
    # 正式运行
    main()
    logger.log('>>>finish')

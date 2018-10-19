#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = 'c00406647'
# version: v0.1
# date: 2018-10-18


import os
import subprocess
import time
import pexpect


from datetime import datetime as datetime


############  全局变量  ############
ERROR = -1
SUCCESS = 0
LOG_TIME = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time()))
LOG_FILE = "./%s.log" % LOG_TIME
host = "192.168.1.74"
TEST_TIME = 120
TEST_MANY = 5
SHORT_SLEEP = 10
LONG_SLEEP = 60
HUGE_SLEEP = 900
TOOLS_DIR = "tools"


# 函数功能：打印到日志
def print_log(content):
    """
    #函数功能：打印到日志
    :param content: 打印的内容，可以为字符串，也可以为列表，元组
    """
    global LOG_FILE
    if content:
        f = open(LOG_FILE, 'a+')
        try:
            print str(content)
            f.write(str(content)+"\n")
            f.close()
        except Exception:
            f.close()


# 函数功能：打印测试任务名称
def print_task_name(task=""):
    """
    #函数功能：打印测试任务名称
    :param task: 任务名称
    """
    task_name = "\n" + "="*20 + "  " + task + "  " + "="*20
    print_log(task_name)


# 函数功能：终止本地进程
def shutdown_process(process_name):
    """
    功能：关闭指定进程
    :param process_name: 进程名称
    """

    # 全局变量
    global ERROR
    global SUCCESS

    # 局部变量
    ret_val = SUCCESS
    cmd = "ps -ef | grep '%s' | grep -v grep" % process_name

    # 打印表头
    # print_task_name("kill %s" % process_name)

    f = os.popen(cmd)
    for i in f.readlines():
        try:
            process_info = i.split()
            pid = int(process_info[1])
            os.kill(pid, 9)
            time.sleep("0.1")
        except:
            ret_val = ERROR

    f.close()

    return ret_val


# 函数功能：关闭所有打流进程
def off():
    process_list = ["netperf", "netserver", "iperf", "iperf3", "memcached", "memaslap",
                    "ab -c", "nginx", "ping", "qperf", "ConstructTestClient", "/client"]
    for i in process_list:
        shutdown_process(i)


# 函数功能：建立SSH信任关系
def set_ssh_key(host, key_type="password", key_value="Huawei@123"):
    """
    # 函数功能：建立SSH信任关系
    :param host:
    """
    # 局部变量
    ssh = None

    # 判断本端id_rsa是否存在
    if os.path.isfile("/root/.ssh/id_rsa") is False:
        ssh = pexpect.spawn("ssh-keygen -t rsa")
        ssh.sendline("")
        time.sleep(0.2)
        ssh.sendline("")
        time.sleep(0.2)
        ssh.sendline("")
        time.sleep(5)
        ssh.close()
        print "ssh-keygen -t rsa success"

    ssh = pexpect.spawn("ssh-copy-id %s" % host)
    try:
        i = ssh.expect(['password:', 'continue connecting (yes/no)?'], timeout=5)
        if i == 0:
            ssh.sendline(key_value)
            time.sleep(5)
        elif i == 1:
            ssh.sendline("yes")
            ssh.expect("password:")
            ssh.sendline(key_value)
            time.sleep(5)
    except pexpect.EOF:
        ssh.close()
    except Exception, e:
        print "SSH error: %s" % e


# 函数功能：安装软件子进程
def exec_shell_command(cmd, target_host=""):
    """
    # 函数功能：安装软件子进程
    :param cmd: 命令
    :param target_host: 所在主机
    """

    # 局部变量
    ret = 0

    if target_host == "":
        ret = os.system("%s 2>/dev/null 1>/dev/null" % cmd)
    else:
        cmd2 = "ssh %s '%s 2>/dev/null 1>/dev/null' 2>/dev/null 1>/dev/null" % (target_host, cmd)
        ret = os.system(cmd2)

    return ret


# 函数功能：安装程序qperf netperf iperf3.3 ab nginx memcached meinian_udp c1000k
def install_tools():
    """
    # 函数功能：安装程序
    """
    # 全局变量
    global host
    global TOOLS_DIR

    # 局部变量
    current_dir = os.getcwd() + "/" + TOOLS_DIR
    cmd_list = []

    # qperf netperf netserver
    soft_list = ["qperf", "netperf", "netserver"]
    for i in soft_list:
        # 如果不存在则安装,local
        if exec_shell_command("/usr/bin/%s -V" % i, target_host="") != 0:
            del cmd_list[:]
            cmd_list.append("rm -f /usr/bin/%s" % i)
            cmd_list.append("rm -f /usr/sbin/%s" % i)
            cmd_list.append("cp %s/%s /usr/bin/" % (current_dir, i))
            cmd_list.append("cp %s/%s /usr/sbin/" % (current_dir, i))
            cmd_list.append("chmod 777 /usr/bin/%s" % i)
            cmd_list.append("chmod 777 /usr/sbin/%s" % i)
            for j in cmd_list:
                exec_shell_command(cmd=j, target_host="")

        # remote
        if exec_shell_command("/usr/bin/%s -V" % i, target_host=host) != 0:
            del cmd_list[:]
            cmd_list.append("rm -f /usr/bin/%s" % i)
            cmd_list.append("rm -f /usr/sbin/%s" % i)
            for j in cmd_list:
                exec_shell_command(cmd=j, target_host=host)

            os.system("scp %s/%s %s:/usr/bin/" % (current_dir, i, host))
            os.system("scp %s/%s %s:/usr/sbin/" % (current_dir, i, host))
            del cmd_list[:]
            cmd_list.append("chmod 777 /usr/bin/%s" % i)
            cmd_list.append("chmod 777 /usr/sbin/%s" % i)
            for j in cmd_list:
                exec_shell_command(cmd=j, target_host=host)

    # local iperf3
    del cmd_list[:]
    cmd_list.append("rm -f /usr/bin/iperf3")
    cmd_list.append("rm -f /usr/local/bin/iperf3")
    cmd_list.append("rm -f /usr/local/lib/libiperf.so.0")
    cmd_list.append("cp %s/iperf3 /usr/bin/iperf3" % current_dir)
    cmd_list.append("cp %s/iperf3 /usr/local/bin/iperf3" % current_dir)
    cmd_list.append("cp %s/libiperf.so.0 /usr/local/lib/libiperf.so.0" % current_dir)
    cmd_list.append("chmod 777 /usr/bin/iperf3")
    cmd_list.append("chmod 777 /usr/local/bin/iperf3")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host="")

    # remote iperf3
    del cmd_list[:]
    cmd_list.append("rm -f /usr/bin/iperf3")
    cmd_list.append("rm -f /usr/local/bin/iperf3")
    cmd_list.append("rm -f /usr/local/lib/libiperf.so.0")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host=host)

    os.system("scp %s/iperf3 %s:/usr/bin/" % (current_dir, host))
    os.system("scp %s/iperf3 %s:/usr/local/bin/" % (current_dir, host))
    os.system("scp %s/libiperf.so.0 %s:/usr/local/lib/" % (current_dir, host))
    del cmd_list[:]
    cmd_list.append("chmod 777 /usr/bin/iperf3")
    cmd_list.append("chmod 777 /usr/local/bin/iperf3")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host=host)

    # local memcached + memaslap
    del cmd_list[:]
    cmd_list.append("rm -f /usr/bin/memcached")
    cmd_list.append("rm -f /usr/bin/memaslap")
    cmd_list.append("rm -f /usr/lib64/libmemcached.so.11")
    cmd_list.append("rm -f /usr/lib64/libevent-2.0.so.5")
    cmd_list.append("cp %s/memcached /usr/bin/" % current_dir)
    cmd_list.append("cp %s/memaslap /usr/bin/" % current_dir)
    cmd_list.append("cp %s/libmemcached.so.11 /usr/lib64/" % current_dir)
    cmd_list.append("cp %s/libevent-2.0.so.5 /usr/lib64/" % current_dir)
    cmd_list.append("chmod 777 /usr/bin/memcached")
    cmd_list.append("chmod 777 /usr/bin/memaslap")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host="")

    # remote memcached + memaslap
    del cmd_list[:]
    cmd_list.append("rm -f /usr/bin/memcached")
    cmd_list.append("rm -f /usr/bin/memaslap")
    cmd_list.append("rm -f /usr/lib64/libmemcached.so.11")
    cmd_list.append("rm -f /usr/lib64/libevent-2.0.so.5")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host=host)

    os.system("scp %s/memcached %s:/usr/bin/" % (current_dir, host))
    os.system("scp %s/memaslap %s:/usr/bin/" % (current_dir, host))
    os.system("scp %s/libmemcached.so.11 %s:/usr/lib64/" % (current_dir, host))
    os.system("scp %s/libevent-2.0.so.5 %s:/usr/lib64/" % (current_dir, host))
    del cmd_list[:]
    cmd_list.append("chmod 777 /usr/bin/memcached")
    cmd_list.append("chmod 777 /usr/bin/memaslap")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host=host)

    # c1000k local
    del cmd_list[:]
    cmd_list.append("rm -f %s/client" % os.getcwd())
    cmd_list.append("rm -f %s/server" % os.getcwd())
    cmd_list.append("cp %s/client %s/" % (current_dir, os.getcwd()))
    cmd_list.append("cp %s/server %s/" % (current_dir, os.getcwd()))
    cmd_list.append("chmod 777 %s/client" % os.getcwd())
    cmd_list.append("chmod 777 %s/server" % os.getcwd())
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host="")

    # c1000k remote
    del cmd_list[:]
    cmd_list.append("rm -f /root/client")
    cmd_list.append("rm -f /root/server")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host=host)

    os.system("scp %s/client %s:/root/" % (current_dir, host))
    os.system("scp %s/server %s:/root/" % (current_dir, host))
    del cmd_list[:]
    cmd_list.append("chmod 777 /root/client")
    cmd_list.append("chmod 777 /root/server")
    for j in cmd_list:
        exec_shell_command(cmd=j, target_host=host)

    # meinian udp local
    if not os.path.isfile("/root/ConstructTest/Linux/client.sh"):
        del cmd_list[:]
        cmd_list.append("rm -rf /root/ConstructTest*")
        cmd_list.append("cp %s/ConstructTest.zip /root/" % current_dir)
        cmd_list.append("unzip /root/ConstructTest.zip -d /root/")
        for j in cmd_list:
            exec_shell_command(cmd=j, target_host="")

    # remote
    exec_shell_command(cmd="rm -f ConstructTest*", target_host=host)
    del cmd_list[:]
    os.system("scp %s/ConstructTest.zip %s:/root/" % (current_dir, host))
    exec_shell_command(cmd="unzip /root/ConstructTest.zip /root/", target_host=host)


# 函数功能：启动server
def start_server():
    global host

    current_dir = os.getcwd() + "/" + TOOLS_DIR
    exec_shell_command(cmd="rm -f /root/run_scenario_server.sh", target_host=host)
    os.system("scp %s/run_scenario_server.sh %s:/root/" % (current_dir, host))
    exec_shell_command("ssh %s 'sh /root/run_scenario_server.sh &" % host)


# 函数功能：测试空载ping延迟，返回(avg_let,loss_percent,send,recv)的列表
def run_ping(serverip, count=60, byte=64, interval=1.0, many=1):
    """
    功能：测试ping，获取发送packets，接收packets，avg latency
    :param serverip: 服务器IP
    :param count: ping数量
    :param byte: ping包长
    :param interval: ping间隔
    :param many: 测试次数
    """
    # 全局变量
    global SHORT_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    pkt_send = -1
    pkt_recv = -1
    pkt_loss_percent = 0
    avg_lat = -1

    # 打印表头
    print_task_name("ping")
    cmd = "ping %s -c %d -W 5 -s %d -i %f" % (serverip, count, byte, interval)
    print_log(cmd)

    # 判断ping程序是否存在，不存在则退出
    if os.system("ping -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["type"] = "ping"
        sum_result["success"] = 0
        ret_value.append((avg_lat, pkt_loss_percent, pkt_send, pkt_recv))
        print "ERROR: ping not exist"
        return ret_value, sum_result

    for i in range(1, many+1):
        print_log("Round: %d" % i)
        pkt_send = -1
        pkt_recv = -1
        pkt_loss_percent = 0
        avg_lat = -1
        f = os.popen(cmd)
        tmp_ret = f.read().strip()
        f.close()
        # 判断包是否全丢
        if tmp_ret.find("100% packet loss") >= 0:
            pkt_send = count
            pkt_recv = 0
            avg_lat = -1
            pkt_loss_percent = 100
        else:
            tmp_ret = tmp_ret.splitlines()
            lat_str = tmp_ret[-1].split("/")
            unit_str = lat_str[-1].split()
            unit_str = unit_str[-1]
            pkt_str = tmp_ret[-2].split()

            pkt_send = int(pkt_str[0])
            pkt_recv = int(pkt_str[3])
            avg_lat = float(lat_str[4])
            # ping单位判断
            if unit_str == "s":
                avg_lat *= 1000
            elif unit_str == "us":
                avg_lat /= 1000.0
            pkt_loss_percent = (1.0 - float(pkt_recv) / float(pkt_send)) * 100

        # 格式化处理
        avg_lat = round(avg_lat, 3)
        pkt_loss_percent = round(pkt_loss_percent, 2)

        ret_value.append((avg_lat, pkt_loss_percent, pkt_send, pkt_recv))

        # 多次测试之间等待间隔
        if i < many:
            time.sleep(SHORT_SLEEP)

    # 结果分析
    sum_count = 0
    sum_avg_lat = 0
    sum_loss_percent = 0
    sum_send = 0
    sum_recv = 0

    for i in ret_value:
        if i[0] > 0:
            sum_count += 1
            sum_avg_lat += i[0]
            sum_loss_percent += i[1]
            sum_send += i[2]
            sum_recv += i[3]

    if sum_count > 0:
        sum_avg_lat = round(sum_avg_lat/sum_count, 3)
        sum_loss_percent = round(sum_loss_percent/sum_count, 3)
        sum_send = round(sum_send/sum_count, 3)
        sum_recv = round(sum_recv/sum_count, 3)

    sum_result["type"] = "ping"
    sum_result["success"] = sum_count
    sum_result["ping(ms)"] = sum_avg_lat
    sum_result["loss(%)"] = sum_loss_percent
    sum_result["send"] = sum_send
    sum_result["recv"] = sum_recv

    return ret_value, sum_result


# 函数功能：测试qperf，返回qperf延迟的列表
def run_qperf(serverip, test_time=60, byte=64, test_type="udp_lat", many=1):
    """
    # 函数功能：测试空载ping延迟，返回(avg_let,loss_percent,send,recv)的列表
    :param serverip: 服务器IP
    :param test_time: 测试时间
    :param byte: 包长
    :param test_type: 测试类型udp_lat/tcp_lat
    :param many: 测试次数
    """
    # 全局变量
    global SHORT_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    qperf_lat = -1

    # 打印表头
    print_task_name("qperf")
    cmd = "qperf %s -t %d -m %d -vu %s" % (serverip, test_time, byte, test_type)
    print_log(cmd)

    # 判断qperf程序是否存在
    if os.system("qperf -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((qperf_lat,))
        print "ERROR: qperf not exist"
        return ret_value, sum_result

    for i in range(1, many+1):
        print_log("Round: %d" % i)
        qperf_lat = -1
        f = os.popen(cmd)
        tmp_ret = f.readlines()
        f.close()
        for j in tmp_ret:
            if "latency" in j:
                lat_str = j.split()
                qperf_lat = float(lat_str[2])
                if lat_str[-1] == "ms":
                    qperf_lat *= 1000
                elif lat_str[-1] == "s":
                    qperf_lat *= 1000000

        # 格式化处理
        qperf_lat = round(qperf_lat, 1)
        ret_value.append((qperf_lat,))

        # 多次测试之间等待间隔
        if i < many:
            time.sleep(SHORT_SLEEP)

    # 结果分析
    sum_count = 0
    sum_qperf = 0

    for i in ret_value:
        if i[0] > 0:
            sum_count += 1
            sum_qperf += i[0]

    if sum_count > 0:
        sum_qperf = round(sum_qperf/sum_count, 1)

    sum_result["type"] = test_type
    sum_result["success"] = sum_count
    sum_result["byte"] = byte
    sum_result["qperf(us)"] = sum_qperf

    return ret_value, sum_result


# 函数功能：测试单流netperf,UDP_STREAM,TCP_STREAM,TCP_RR,TCP_CRR,UDP_RR
# 返回值：(tx_bw,rx_bw,tcp_rr,tcp_crr,udp_rr)
def run_one_netperf(serverip, port=12865, test_type="TCP_STREAM", test_time=60, byte=64, many=1):
    """
    #函数功能：测试单流netperf,UDP_STREAM,TCP_STREAM,TCP_RR,TCP_CRR,UDP_RR
    :param serverip: 服务器IP
    :param test_type: 测试类型TCP_STREAM,UDP_STREAM,TCP_RR,TCP_CRR,UDP_RR
    :param test_time: 测试时间
    :param byte: 包长
    :param many: 测试次数
    """

    # 全局变量
    global LONG_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    tx_bw = -1
    rx_bw = -1
    tcp_rr = -1
    tcp_crr = -1
    udp_rr = -1

    test_type = test_type.upper()
    # 打印表头
    print_task_name("netperf %s" % test_type)

    # 测试类型合法性校验
    if test_type == "TCP_STREAM" or test_type == "UDP_STREAM":
        cmd = "netperf -H %s -p %d -t %s -l %d -- -m %d -R 1" % (serverip, port, test_type, test_time, byte)
    elif test_type == "TCP_RR" or test_type == "TCP_CRR" or test_type == "UDP_RR":
        cmd = "netperf -H %s -p %d -t %s -l %d -- -r %d" % (serverip, port, test_type, test_time, byte)
    else:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: netperf syntax error"
        return ret_value, sum_result

    # 判断netperf程序是否存在，不存在则退出
    if os.system("netperf -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: netperf not exist"
        return ret_value, sum_result

    print_log(cmd)
    for i in range(1, many+1):
        print_log("Round: %d" % i)
        tx_bw = -1
        rx_bw = -1
        tcp_rr = -1
        tcp_crr = -1
        udp_rr = -1
        try:
            f = os.popen(cmd)
            tmp_ret = f.readlines()
            f.close()
            # 输出正常
            if test_type == "TCP_STREAM":
                tx_str = tmp_ret[-1].split()
                tx_bw = float(tx_str[-1])
                rx_bw = tx_bw
            elif test_type == "UDP_STREAM":
                tx_str = tmp_ret[-3].split()
                rx_str = tmp_ret[-2].split()
                tx_bw = float(tx_str[-1])
                rx_bw = float(rx_str[-1])
            elif test_type == "TCP_RR":
                rr_str = tmp_ret[-2].split()
                tcp_rr = float(rr_str[-1])
            elif test_type == "TCP_CRR":
                crr_str = tmp_ret[-2].split()
                tcp_crr = float(crr_str[-1])
            elif test_type == "UDP_RR":
                udp_rr_str = tmp_ret[-2].split()
                udp_rr = float(udp_rr_str[-1])
        except:
            tx_bw = -1
            rx_bw = -1
            tcp_rr = -1
            tcp_crr = -1
            udp_rr = -1

        # 格式化处理
        tx_bw = round(tx_bw)
        rx_bw = round(rx_bw)
        tcp_rr = round(tcp_rr)
        tcp_crr = round(tcp_crr)
        udp_rr = round(udp_rr)
        ret_value.append((tx_bw, rx_bw, tcp_rr, tcp_crr, udp_rr,))

        # 多次测试之间停留xx seconds
        if i < many:
            time.sleep(LONG_SLEEP)

    # 结果分析
    sum_count = 0
    sum_tx_bw = 0
    sum_rx_bw = 0
    sum_tcp_rr = 0
    sum_tcp_crr = 0
    sum_udp_rr = 0

    for i in ret_value:
        if test_type == "TCP_STREAM":
            if i[0] > 0:
                sum_count += 1
                sum_tx_bw += i[0]
        elif test_type == "UDP_STREAM":
            if i[0] > 0 and i[1] > 0:
                sum_count += 1
                sum_tx_bw += i[0]
                sum_rx_bw += i[1]
        elif test_type == "TCP_RR":
            if i[2] > 0:
                sum_count += 1
                sum_tcp_rr += i[2]
        elif test_type == "TCP_CRR":
            if i[3] > 0:
                sum_count += 1
                sum_tcp_crr += i[3]
        elif test_type == "UDP_RR":
            if i[4] > 0:
                sum_count += 1
                sum_udp_rr += i[4]

    sum_result["type"] = test_type
    sum_result["success"] = sum_count
    sum_result["byte"] = byte

    if sum_count > 0:
        if test_type == "TCP_STREAM":
            sum_tx_bw = round(sum_tx_bw/sum_count)
            sum_result["tx_bw"] = sum_tx_bw
        elif test_type == "UDP_STREAM":
            sum_tx_bw = round(sum_tx_bw/sum_count)
            sum_rx_bw = round(sum_rx_bw/sum_count)
            sum_result["tx_bw"] = sum_tx_bw
            sum_result["rx_bw"] = sum_rx_bw
        elif test_type == "TCP_RR":
            sum_tcp_rr = round(sum_tcp_rr/sum_count)
            sum_result["tcp_rr"] = sum_tcp_rr
        elif test_type == "TCP_CRR":
            sum_tcp_crr = round(sum_tcp_crr/sum_count)
            sum_result["tcp_crr"] = sum_tcp_crr
        elif test_type == "UDP_RR":
            sum_udp_rr = round(sum_udp_rr/sum_count)
            sum_result["udp_rr"] = sum_udp_rr

    return ret_value, sum_result


# 函数功能：测试ab -c 100 -n 5000000，获取RPS、avg time、100%time
def run_one_ab(serverip, port=80, page="/", user_num=100, total_count=5000000, many=1):
    """
    #函数功能：测试ab -c 100 -n 5000000，获取RPS、avg time、100%time
    :param serverip: 服务器IP
    :param port: web port
    :param page: 页面路径
    :param user_num: 并发用户
    :param total_count: 总请求数
    :param many: 测试几次
    """
    # 全局变量、
    global LONG_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    rps = 0
    avg_time = 0
    longest_time = 0

    # 打印表头
    print_task_name("ab -c %d" % user_num)
    cmd = "ab -c %d -n %d http://%s:%s%s 2>/dev/null" % (user_num, total_count, serverip, port, page)
    print_log(cmd)

    # 判断ab是否存在
    if os.system("ab -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: ab not exist"
        return ret_value, sum_result

    for i in range(1, many + 1):
        print_log("Round: %d" % i)
        f = os.popen(cmd)
        tmp_ret = f.readlines()
        f.close()
        key = "longest request"
        bfinish = False

        rps = -1
        avg_time = -1
        longest_time = -1

        for j in tmp_ret:
            if key in j:
                bfinish = True
                break

        if bfinish:
            for j in tmp_ret:
                if "Requests per second" in j:
                    rps_str = j
                    rps_str = rps_str.split(" ")
                    rps = float(rps_str[-3])
                elif "[ms] (mean)" in j:
                    avg_str = j
                    avg_str = avg_str.split(" ")
                    avg_time = float(avg_str[-3])
                elif "longest request" in j:
                    longest_str = j
                    longest_str = longest_str.split(" ")
                    longest_time = float(longest_str[-3])

        # 数据格式化处理
        rps = round(rps)
        avg_time = round(avg_time)
        longest_time = round(longest_time)
        ret_value.append((rps, avg_time, longest_time,))

        # 多次测试之间测试等待
        if i < many:
            time.sleep(LONG_SLEEP)

    # 结果分析
    sum_count = 0
    sum_rps = 0
    sum_time = 0
    sum_longest = 0

    for i in ret_value:
        if i[0] > 0:
            sum_count += 1
            sum_rps += i[0]
            sum_time += i[1]
            if i[2] > sum_longest:
                sum_longest = i[2]

    if sum_count > 0:
        sum_rps = round(sum_rps/sum_count)
        sum_time = round(sum_time/sum_count)
        sum_longest = longest_time

    sum_result["success"] = sum_count
    sum_result["rps"] = sum_rps
    sum_result["time(ms)"] = sum_time
    sum_result["longest(ms)"] = sum_longest

    return ret_value, sum_result


# 函数功能：测试memcached单流TPS
def run_one_memcached(serverip, port=11211, test_time=60, threads=16, concurrency=256, byte=100, many=1):
    """
    函数功能：测试memcached单流TPS
    :param serverip: 服务器IP地址
    :param port: memcached监听端口
    :param test_time: 测试时长-t
    :param threads: 线程数-T
    :param concurrency: 并发用户-c
    :param byte: memcached包长-B
    :param many: 测试次数
    """
    # 全局变量
    global SHORT_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    tps = 0

    # 打印表头
    print_task_name("one user memcached")
    cmd = "memaslap -s %s:%d -t %ds -T %d -c %d -X %dB" % (serverip, port, test_time, threads, concurrency, byte)

    # 判断memaslap是否存在
    if os.system("memaslap -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: memaslap not exist"
        return ret_value, sum_result

    for i in range(1, many + 1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        f = os.popen(cmd)
        tmp_ret = f.readlines()
        f.close()
        key = "Run time"
        bfinish = False

        tps = -1
        tps_str = ""
        for j in tmp_ret:
            if key in j:
                bfinish = True
                tps_str = j
                tps_str = tps_str.split(" ")
                tps = float(tps_str[-3])

        # 数据处理
        tps = round(tps)
        ret_value.append((tps,))

        # 多次测试之间等待
        if i < many:
            time.sleep(SHORT_SLEEP)

    # 结果分析
    sum_count = 0
    sum_tps = 0

    for i in ret_value:
        if i[0] > 0:
            sum_count += 1
            sum_tps += i[0]

    sum_tps = round(sum_tps/sum_count)

    sum_result["success"] = sum_count
    sum_result["user"] = concurrency
    sum_result["byte"] = byte
    sum_result["tps"] = sum_tps

    return ret_value, sum_result


# 函数功能：scp 10G文件速率测试
def run_scp_speed(serverip, size=10240, many=1):
    """
    #函数功能：scp 10G文件速率测试
    :param serverip: 服务器IP
    :param size: 文件大小，单位MB
    :param many: 测试次数
    """
    # 全局变量
    global SHORT_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    copy_speed = 0

    # 打印表头
    print_task_name("SCP Test")
    filename = "/root/%dG" % (size/1024)
    cmd = "dd if=/dev/zero of=%s bs=1M count=%d 2>/dev/null 1>/dev/null" % (filename, size)
    os.system(cmd)
    cmd = "scp %s root@%s:" % (filename, serverip)
    print_log(cmd)

    for i in range(1, many + 1):
        print_log("Round: %d" % i)
        tmp_file = "/tmp/scp.log"
        os.system("rm -f %s" % tmp_file)

        copy_speed = -1
        cmd_shell = "script -q %s -c '%s'" % (tmp_file, cmd)
        os.system(cmd_shell)
        f = open(tmp_file)
        tmp_ret = f.read().splitlines()
        f.close()

        for j in tmp_ret:
            if "100%" in j:
                copy_str = j.split(" ")
                for k in copy_str:
                    if "MB/s" in k or "KB/s" in k:
                        copy_str = k
                        index = copy_str.find("MB/s")
                        if index >= 0:
                            speed_str = copy_str[0:index]
                            copy_speed = float(speed_str)
                        else:
                            index = copy_str.find("KB/s")
                            speed_str = copy_str[0:index]
                            copy_speed = float(speed_str)/1000.

                        break
                break

        os.system("rm -f %s" % tmp_file)
        # 数据处理
        try:
            copy_speed = round(copy_speed)
        except:
            copy_speed = -1

        ret_value.append((copy_speed,))
        # 多次测试之间停留
        if i < many:
            time.sleep(SHORT_SLEEP)

    # 结果分析
    sum_count = 0
    sum_speed = 0
    for i in ret_value:
        if i[0] > 0:
            sum_count += 0
            sum_speed += i[0]

    if sum_count > 0:
        sum_speed = round(sum_speed/sum_count)
    sum_result["success"] = sum_count
    sum_result["scp_speed(MB/s)"] = sum_speed

    return ret_value, sum_result


# 函数功能：美年大健康UDP乱序检测
def run_meinian_udp_check(serverip, check_num=20, many=1):
    """
    #函数功能：美年大健康UDP乱序检测
    :param serverip:  服务器IP
    :param check_num: 取屏幕输出的多少次计算平均值
    :param many: 测试次数
    """
    # 全局变量
    global LONG_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    udp_time = 0

    # 打印表头
    print_task_name("meinian UDP check")
    cmd = "sh /root/ConstructTest/Linux/client.sh %s" % serverip

    # 判断程序是否存在
    if not os.path.isfile("/root/ConstructTest/Linux/client.sh"):
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: memaslap not exist"
        return ret_value, sum_result

    for i in range(1, many + 1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))

        os.system("rm -f ./TestReport.txt 2>&1 > /dev/null")
        os.system(cmd + " 2>&1 > /dev/null")
        f = subprocess.Popen('tail -F ./TestReport.txt', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        udp_time = -1
        peak_num = 0
        tmp_count = 0

        while True:
            line = f.stdout.readline()
            if "udp Test" in line:
                peak_num += 1
                if peak_num > check_num:
                    break
                udp_str = line.split(" ")
                tmp_count += float(udp_str[-2])
                print udp_str[-2],

        # 结束meinian udp任务
        shutdown_process("ConstructTestClient")
        time.sleep(30)

        # 数据处理
        udp_time = tmp_count / check_num
        udp_time = round(udp_time)

        ret_value.append((udp_time,))

        # 多次测试之间停留
        if i < many:
            time.sleep(LONG_SLEEP)

    # 结果分析
    sum_count = 0
    sum_time = 0

    for i in ret_value:
        if i[0] > 0:
            sum_count += 1
            sum_time += i[0]

    sum_time = round(sum_time/sum_count)
    sum_result["success"] = sum_count
    sum_result["time(ms)"] = sum_time

    return ret_value, sum_result


# 函数功能：多流发送带宽检测
def run_multi_user_netperf_send_bandwidth(serverip, flow=16, base_port=7001, type="TCP_STREAM", test_time=1200, byte=1440, many=1):
    """
    #函数功能：多流带宽检测
    :param serverip: 服务器地址
    :param flow: 几条流
    :param base_port: netserver监听起始端口
    :param type: 测试类型,默认TCP_STREAM
    :param test_time: 测试时长,默认1200
    :param byte: 包长,默认1440
    :param many: 测试次数
    """
    # 全局变量
    global SHORT_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    tcp_bw = 0
    cmd = "netperf %s %d flow" % (type, flow)

    # 打印表头
    print_task_name(cmd)
    print_log(cmd)

    # 判断netperf程序是否存在，不存在则退出
    if os.system("netperf -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: netperf not exist"
        return ret_value, sum_result

    for i in range(1, many+1):
        print_log("Round: %d" % i)
        tcp_bw = -1
        for j in range(1, flow+1):
            port = base_port + j - 1
            cmd = "netperf -H %s -p %d -t %s -l %d -- -m %d 2>&1 > /dev/null &" % (serverip, port, type, test_time, byte)
            os.system(cmd)

        # 采集数据
        time.sleep(30)

        cmd = "sar -n DEV 1 60 | grep eth"
        f = os.popen(cmd)
        tmp_ret = f.readlines()
        for j in tmp_ret:
            if "Average" in j:
                bw_str = j.split(" ")
                count = 0
                for k in bw_str:
                    if k:
                        count += 1
                        if count == 6:
                            tcp_bw = float(k)

        f.close()
        shutdown_process("netperf")

        # 数据处理
        tcp_bw = round(tcp_bw)
        ret_value.append((tcp_bw,))

        # 多次测试之间等待
        if i < many:
            time.sleep(SHORT_SLEEP)

    # 结果分析
    sum_count = 0
    sum_bw = 0
    for i in ret_value:
        if i[0] > 0:
            sum_count += 0
            sum_bw += i[0]

    if sum_count > 0:
        sum_bw = round(sum_bw/sum_count)
    sum_result["success"] = sum_count
    sum_result["type"] = type
    sum_result["tx_bw"] = sum_bw

    return ret_value, sum_result


# 函数功能：多流TCP_RR，改到这里
def run_multi_user_tcp_rr(serverip, flow=16, base_port=7001, test_type="TCP_RR", test_time=120, byte=64, many=1):
    """
    #函数功能：多流TCP_RR
    :param serverip: 服务器IP
    :param flow: 流数
    :param base_port: 起始端口
    :param test_type: 测试类型TCP_RR
    :param test_time: 测试时长
    :param byte: 测试包长
    :param many: 测试次数
    """
    # 全局变量
    global SHORT_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    tcp_rr = -1
    cmd = "netperf %s %d flow" % (test_type, flow)

    # 打印表头
    print_task_name(cmd)
    print_log(cmd)

    # 判断netperf程序是否存在，不存在则退出
    if os.system("netperf -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: netperf not exist"
        return ret_value, sum_result

    for i in range(1, many + 1):
        print_log("Round: %d" % i)
        tcp_rr = 0

        try:
            # 临时文件
            tmp_prefix = "/tmp/netperf_rr_"
            cmd = "rm -f %s* 2>&1 > /dev/null" % tmp_prefix
            os.system(cmd)

            for j in range(1, flow+1):
                port = base_port + j - 1
                cmd = "netperf -H %s -p %d -t %s -l %d -- -r %d 2>&1 > %s%d.log &" \
                       % (serverip, port, test_type, test_time, byte, tmp_prefix, port)
                os.system(cmd)

            # 获取结果
            time.sleep(5 + test_time)
            for j in range(1, flow+1):
                port = base_port + j - 1
                tmp_file = "%s%d.log" % (tmp_prefix, port)
                f = open(tmp_file)
                tmp_ret = f.read().splitlines()
                f.close()
                rr_str = tmp_ret[-2].strip().split(" ")[-1]
                tcp_rr += float(rr_str)
        except Exception:
            tcp_rr = -1

        # 数据格式化
        tcp_rr = round(tcp_rr)
        ret_value.append((tcp_rr,))

        # 清理临时文件
        time.sleep(2)
        cmd = "rm -f %s* 2>&1 > /dev/null" % (tmp_prefix)
        os.system(cmd)

        # 多次测试之间停留
        if i < many:
            time.sleep(SHORT_SLEEP)

    return ret_value


#函数功能：多流TCP_CRR
def run_multi_user_tcp_crr(serverip, flow=16, base_port=7001, type="TCP_CRR", test_time=120, byte=64, many=1):
    """
    #函数功能：多流TCP_CRR
    :param serverip: 服务器IP
    :param flow: 流数
    :param base_port: 起始端口
    :param type: 测试类型TCP_RR
    :param test_time: 测试时长
    :param byte: 测试包长
    :param many: 测试次数
    """
    #局部变量
    ret_value = []
    sum_result = {}
    tcp_crr = -1
    cmd = "netperf %s %d flow" % (type, flow)

    # 打印表头
    print_task_name(cmd)

    # 判断netperf程序是否存在，不存在则退出
    if os.system("netperf -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: netperf not exist"
        return ret_value, sum_result

    for i in range(1, many + 1):
        cmd = "netperf %s %d flow" % (type, flow)
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        tcp_crr = 0

        #临时文件
        tmp_prefix = "/tmp/netperf_crr_"
        cmd = "rm -f %s* 2>&1 > /dev/null" % (tmp_prefix)
        os.system(cmd)

        for j in range(1, flow+1):
            port = base_port + j -1
            cmd = "netperf -H %s -p %d -t %s -l %d -- -r %d 2>&1 > %s%d.log &" \
                   % (serverip, port, type, test_time, byte, tmp_prefix, port)
            os.system(cmd)

        #获取结果
        time.sleep(5 + test_time)
        for j in range(1, flow+1):
            #有可能netperf报错
            try:
                port = base_port + j - 1
                tmp_file = "%s%d.log" % (tmp_prefix, port)
                f = open(tmp_file)
                tmp_ret = f.read().splitlines()
                crr_str = tmp_ret[-2].strip().split(" ")[-1]
                tcp_crr += float(crr_str)
                f.close()
            except:
                tcp_crr += 0

        #数据格式化
        tcp_crr = round(tcp_crr)
        ret_value.append((tcp_crr,))

        #清理临时文件
        time.sleep(2)
        cmd = "rm -f %s* 2>&1 > /dev/null" % tmp_prefix
        os.system(cmd)

        #多次测试之间停留10s
        if i < many:
            time.sleep(60)

    return ret_value


#函数功能：多流memcached,默认4条流
def run_multi_user_memcached(serverip, base_port=9001, flow=4, test_time=60, threads=16, concurrency=256, byte=100, many=1):
    """
    #函数功能：多流memcached
    :param serverip: 服务器IP
    :param base_port: 起始端口
    :param flow: 几条流
    :param test_time: 测试时长
    :param threads: 每条流线程数
    :param concurrency: 每条流并发用户，默认256
    :param byte: 包长
    :param many:测试次数
    """
    # 全局变量
    global SHORT_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}

    #打印表头
    cmd = "memcached %d flow" % flow
    print_task_name(cmd)

    # 判断memaslap是否存在
    if os.system("memaslap -V 2>/dev/null 1>/dev/null") != 0:
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: memaslap not exist"
        return ret_value, sum_result

    for i in range(1, many + 1):
        cmd = "memcached %d flow" % flow
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        tps = 0

        # 临时文件
        tmp_prefix = "/tmp/memcached_"
        cmd = "rm -f %s* 2>&1 > /dev/null" % (tmp_prefix)
        os.system(cmd)

        #发送测试命令
        for j in range(1, flow+1):
            port = base_port + j -1
            tmp_file = "%s%d.log" % (tmp_prefix, port)
            cmd = "memaslap -s %s:%d -t %ds -T %d -c %d -X %dB 2>&1 > %s &" \
                  % (serverip, port, test_time, threads, concurrency, byte, tmp_file)
            os.system(cmd)

        #等待结束
        time.sleep(test_time+10)

        #采集结果
        for j in range(1, flow+1):
            port = base_port + j - 1
            tmp_file = "%s%d.log" % (tmp_prefix, port)

            #只有当文件存在时，才读取
            if os.path.isfile(tmp_file):
                f = open(tmp_file)
                tmp_ret = f.read().strip().splitlines()
                f.close()
                for k in tmp_ret:
                    if "Run time" in k:
                        tps_str = k
                        tps_str = tps_str.split(" ")
                        tps += float(tps_str[-3])
                        break
            else:
                tps += 0

        #数据处理
        ret_value.append((tps,))

        #清理临时文件
        tmp_prefix = "/tmp/memcached_"
        cmd = "rm -f %s* 2>&1 > /dev/null" % (tmp_prefix)
        os.system(cmd)

        #多次测试之间停留
        if i < many:
            time.sleep(SHORT_SLEEP)

    return ret_value


#函数功能，测试c1000k并发连接数，待处理平均数
def run_multi_user_c1000k(serverip, flow=2, base_port=11000, many=1):
    """
    #函数功能，测试c1000k并发连接数
    :param serverip:
    :param flow:
    :param base_port:
    :param many:
    """
    # 全乎变量
    global HUGE_SLEEP
    # 局部变量
    ret_value = []
    sum_result = {}
    cmd = "c1000k %d flow test" % flow

    # 打印表头
    print_task_name(cmd)
    # 判断程序是否存在
    if not os.path.isfile("%s/client" % os.getcwd()):
        sum_result["success"] = 0
        ret_value.append((-1,))
        print "ERROR: c1000k client not exist"
        return ret_value, sum_result

    for i in range(1, many + 1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))

        # 执行c1000k测试
        for j in range(1, flow + 1):
            port = base_port + (j-1)*2000
            cmd = "%s/client %s %d 2>&1 > /dev/null &" % (os.getcwd(), serverip, port)
            os.system(cmd)
            time.sleep(10)

        # 获取连接数
        old = new = 0
        max_conn = 0
        same_time = 0

        # 采集连接数
        while True:
            cmd = "ss -s"
            f = os.popen(cmd)
            tmp_ret = f.read().strip().splitlines()

            for k in tmp_ret:
                if "estab" in k:
                    pos1 = k.find("estab") + len("estab")
                    pos2 = k.find(",", pos1)
                    new = int(k[pos1:pos2].strip())
                    f.close()

            # 获取最大连接数
            if new > max_conn:
                max_conn = new

            # 数据与上次相比，变化了没有
            if new == old:
                same_time += 1
            else:
                same_time = 0

            # 连续N次连接数不更新，认为结束，退出采集
            if same_time > 10:
                break

            # 进入下一次采集
            old = new
            time.sleep(10)

        # 关闭client程序
        process_name = "%s/client" % os.getcwd()
        print "our time is short!"
        print process_name
        shutdown_process(process_name)

        # 结果处理
        ret_value.append((max_conn,))

        # 2次测试程序间隔600s以上,让计算节点tcp老化
        if i < many:
            time.sleep(HUGE_SLEEP)

    return ret_value


############  main函数入口  ############
def main():
    global host
    global TEST_TIME
    global TEST_MANY
    off()
    set_ssh_key(host=host, key_value="huawei")
    install_tools()
    '''
    ret = run_ping(host, count=TEST_TIME, byte=64, interval=1, many=TEST_MANY)
    print_log(ret)

    ret = run_qperf(host, test_time=TEST_TIME, byte=64, test_type="udp_lat", many=TEST_MANY)
    print_log(ret)

    ret = run_qperf(host, test_time=TEST_TIME, byte=64, test_type="tcp_lat", many=TEST_MANY)
    print_log(ret)

    ret = run_qperf(host, test_time=TEST_TIME, byte=65000, test_type="udp_lat", many=TEST_MANY)
    print_log(ret)

    netperf = ["TCP_STREAM", "UDP_STREAM", "TCP_RR", "TCP_CRR", "UDP_RR"]
    for i in netperf:
        test_byte = 64
        if i == "TCP_STREAM":
            test_byte = 1440
        ret = run_one_netperf(host, test_type=i, test_time=TEST_TIME, byte=test_byte, many=TEST_MANY)
        print_log(ret)

    ret = run_one_ab(host, user_num=100, total_count=1000000, many=TEST_MANY)
    print_log(ret)

    ret = run_one_memcached(host, port=22122, test_time=TEST_TIME, threads=16, concurrency=256, byte=100, many=TEST_MANY)
    print_log(ret)

    ret = run_scp_speed(host, size=1024, many=TEST_MANY)
    print_log(ret)

    ret = run_meinian_udp_check(host, check_num=20, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_netperf_send_bandwidth(host, flow=16, base_port=7001, type="TCP_STREAM", test_time=TEST_TIME, byte=1440, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_tcp_rr(host, flow=16, base_port=7001, test_type="TCP_RR", test_time=TEST_TIME, byte=64, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_tcp_crr(host, flow=16, base_port=7001, type="TCP_CRR", test_time=TEST_TIME, byte=64, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_c1000k(host, flow=1, base_port=11000, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_memcached(host, test_time=TEST_TIME, many=TEST_MANY)
    print_log(ret)
    '''

if __name__ == '__main__':
    main()
    print_log("work complete! all done.")

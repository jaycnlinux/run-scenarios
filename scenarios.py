#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = 'c00406647'


import os
import subprocess
import time
from datetime import datetime as datetime



############  全局变量  ############
ERROR = -1
SUCCESS = 0
LOG_TIME = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(time.time()))
LOG_FILE = "./%s.log" % LOG_TIME


#函数功能：打印到日志
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
        finally:
            f.close()


#函数功能：打印测试任务名称
def print_task_name(task=""):
    """
    #函数功能：打印测试任务名称
    :param task: 任务名称
    """

    task_name = "=" * 20 + "  " + task + "  " + "=" * 20
    print_log(task_name)


#函数功能：终止本地进程
def shutdown_process(process_name):
    """
    功能：关闭指定进程
    :param process_name: 进程名称
    """

    #全局变量
    global ERROR
    global SUCCESS

    #局部变量
    ret_val = SUCCESS
    cmd = "ps -ef | grep '%s' | grep -v grep" % process_name


    #打印表头
    #print_task_name("kill %s" % process_name)

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


#函数功能：关闭所有打流进程
def off():
    process_list = ["netperf", "netserver", "iperf", "iperf3", "memcached", "memaslap",
                    "ab -c", "nginx", "ping", "qperf", "ConstructTestClient", "/client"]
    for i in process_list:
        shutdown_process(i)


#函数功能：启动server
def start_server():
    pass


#函数功能：测试空载ping延迟，返回(avg_let,loss_percent,send,recv)的列表
def run_ping(serverip, count=60, byte=64, interval=1.0, many=1):
    """
    功能：测试ping，获取发送packets，接收packets，avg latency
    :param serverip: 服务器IP
    :param count: ping数量
    :param byte: ping包长
    :param interval: ping间隔
    :param many: 测试次数
    """

    #局部变量
    ret_value = []

    #打印表头
    print_task_name("ping")

    cmd = "ping %s -c %d -W 5 -s %d -i %f" % (serverip, count, byte, interval)
    for i in range(1, many+1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))

        pkt_send = -1
        pkt_recv = -1
        pkt_loss_percent = 0
        avg_lat = -1

        f = os.popen(cmd)
        tmp_ret = f.read().strip()
        #判断包是否全丢
        if tmp_ret.find("100% packet loss") >= 0:
            tmp_ret = tmp_ret.splitlines()
            pkt_str = tmp_ret[-1].split()

            pkt_send = int(pkt_str[0])
            pkt_recv = int(pkt_str[3])
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
            #ping单位判断
            if unit_str == "s":
                avg_lat *= 1000
            elif unit_str == "us":
                avg_lat /= 1000.0
            pkt_loss_percent = (1.0 - float(pkt_recv)/float(pkt_send))*100

        f.close()
        #格式化处理
        avg_lat = round(avg_lat, 2)
        pkt_loss_percent = round(pkt_loss_percent, 2)

        ret_value.append((avg_lat, pkt_loss_percent, pkt_send, pkt_recv))

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能：测试qperf，返回qperf延迟的列表
def run_qperf(serverip, test_time=60, byte=64, type="udp_lat", many=1):
    """
    #函数功能：测试空载ping延迟，返回(avg_let,loss_percent,send,recv)的列表
    :param serverip: 服务器IP
    :param test_time: 测试时间
    :param byte: 包长
    :param type: 测试类型udp_lat/tcp_lat
    :param many: 测试次数
    """

    #局部变量
    ret_value = []

    #打印表头
    print_task_name("qperf")

    cmd = "qperf %s -t %d -m %d -vu %s" % (serverip, test_time, byte, type)
    for i in range(1, many+1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        qperf_lat = -1
        f = os.popen(cmd)
        tmp_ret = f.readlines()
        for j in tmp_ret:
            if "latency" in j:
                lat_str = j.split()
                qperf_lat = float(lat_str[2])
                if lat_str[-1] == "ms":
                    qperf_lat *= 1000
                elif lat_str[-1] == "s":
                    qperf_lat *= 1000000

        f.close()

        #格式化处理
        qperf_lat = round(qperf_lat)
        ret_value.append((qperf_lat,))

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能：测试单流netperf,UDP_STREAM,TCP_STREAM,TCP_RR,TCP_CRR,UDP_RR
#返回值：(tx_bw,rx_bw,tcp_rr,tcp_crr,udp_rr)
def run_one_netperf(serverip, port=12865, test_type="TCP_STREAM", test_time=60, byte=64, many=1):
    """
    #函数功能：测试单流netperf,UDP_STREAM,TCP_STREAM,TCP_RR,TCP_CRR,UDP_RR
    :param serverip: 服务器IP
    :param test_type: 测试类型TCP_STREAM,UDP_STREAM,TCP_RR,TCP_CRR,UDP_RR
    :param test_time: 测试时间
    :param byte: 包长
    :param many: 测试次数
    """

    #局部变量
    ret_value = []
    tx_bw = -1
    rx_bw = -1
    tcp_rr = -1
    tcp_crr = -1
    udp_rr = -1
    syntax_error = False

    test_type = test_type.upper()
    #打印表头
    print_task_name("netperf %s" % test_type)

    # 测试类型合法性校验
    if test_type == "TCP_STREAM" or test_type == "UDP_STREAM":
        cmd = "netperf -H %s -p %d -t %s -l %d -- -m %d -R 1" % (serverip, port, test_type, test_time, byte)
    elif test_type == "TCP_RR" or test_type == "TCP_CRR" or test_type == "UDP_RR":
        cmd = "netperf -H %s -p %d -t %s -l %d -- -r %d" % (serverip, port, test_type, test_time, byte)
    else:
        cmd = "fail: netperf syntax error"
        syntax_error = True

    for i in range(1,many+1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))

        tx_bw = -1
        rx_bw = -1
        tcp_rr = -1
        tcp_crr = -1
        udp_rr = -1
        if not syntax_error:

            try:
                f = os.popen(cmd)
                tmp_ret = f.readlines()

                #输出正常
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

                f.close()
            except:
                tx_bw = -1
                rx_bw = -1
                tcp_rr = -1
                tcp_crr = -1
                udp_rr = -1

        #格式化处理
        tx_bw = round(tx_bw)
        rx_bw = round(rx_bw)
        tcp_rr = round(tcp_rr)
        tcp_crr = round(tcp_crr)
        udp_rr = round(udp_rr)
        ret_value.append((tx_bw, rx_bw, tcp_rr, tcp_crr, udp_rr,))

        #多次测试之间停留xx seconds
        if i < many:
            time.sleep(60)

    return ret_value


#函数功能：测试ab -c 100 -n 5000000，获取RPS、avg time、100%time
def run_one_ab(serverip, port=80, page="/", user_num=100, total_count=1000000, many=1):
    """
    #函数功能：测试ab -c 100 -n 5000000，获取RPS、avg time、100%time
    :param serverip: 服务器IP
    :param port: web port
    :param page: 页面路径
    :param user_num: 并发用户
    :param total_count: 总请求数
    :param many: 测试几次
    """
    # 局部变量
    ret_value = []
    rps = 0
    avg_time = 0
    longest_time = 0

    # 打印表头
    print_task_name("ab -c %d" % user_num)

    cmd = "ab -c %d -n %d http://%s:%s%s 2>/dev/null" % (user_num, total_count, serverip, port, page)
    for i in range(1, many + 1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        f = os.popen(cmd)
        tmp_ret = f.readlines()
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

        #数据格式化处理
        rps = round(rps)
        avg_time = round(avg_time)
        longest_time = round(longest_time)
        ret_value.append((rps, avg_time, longest_time,))
        f.close()

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能：测试memcached单流TPS
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

    # 局部变量
    ret_value = []
    tps = 0

    # 打印表头
    print_task_name("one user memcached")

    cmd = "memaslap -s %s:%d -t %ds -T %d -c %d -X %dB" % (serverip, port, test_time, threads, concurrency, byte)

    for i in range(1, many + 1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        f = os.popen(cmd)
        tmp_ret = f.readlines()
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

        #数据处理
        tps = round(tps)
        ret_value.append((tps,))

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能：scp 10G文件速率测试
def run_scp_speed(serverip, size=10240, many=1):
    """
    #函数功能：scp 10G文件速率测试
    :param serverip: 服务器IP
    :param size: 文件大小，单位MB
    :param many: 测试次数
    """

    # 局部变量
    ret_value = []
    copy_speed = 0

    # 打印表头
    print_task_name("SCP Test")
    filename = "/root/%dG" % (size/1024)
    cmd = "dd if=/dev/zero of=%s bs=1M count=%d" % (filename, size)
    os.system(cmd)

    cmd = "scp %s root@%s:" % (filename, serverip)
    for i in range(1, many + 1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))
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


        #数据处理
        copy_speed = round(copy_speed)
        ret_value.append((copy_speed,))

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能：美年大健康UDP乱序检测
def run_meinian_udp_check(serverip, check_num=20, many=1):
    """
    #函数功能：美年大健康UDP乱序检测
	:param serverip:  服务器IP
	:param check_num: 取屏幕输出的多少次计算平均值
	:param many: 测试次数
	"""

    # 局部变量
    ret_value = []
    udp_time = 0

    # 打印表头
    print_task_name("meinian UDP check")
    cmd = "sh /root/ConstructTest/Linux/client.sh %s" % serverip

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

        #结束meinian udp任务
        shutdown_process("ConstructTestClient")
        time.sleep(30)

        #数据处理
        udp_time = tmp_count / check_num
        udp_time = round(udp_time)

        ret_value.append((udp_time,))

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能：多流发送带宽检测
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

    #局部变量
    ret_value = []
    tcp_bw = 0
    cmd = "netperf %s %d flow" % (type, flow)

    # 打印表头
    print_task_name(cmd)

    for i in range(1, many+1):
        cmd = "netperf %s %d flow" % (type, flow)
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        tcp_bw = -1
        for j in range(1, flow+1):
            port = base_port + j - 1
            cmd = "netperf -H %s -p %d -t %s -l %d -- -m %d 2>&1 > /dev/null &" % (serverip, port, type, test_time, byte)
            os.system(cmd)

        #采集数据
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

        #数据处理
        tcp_bw = round(tcp_bw)
        ret_value.append((tcp_bw,))

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能：多流TCP_RR
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

    #局部变量
    ret_value = []
    tcp_rr = -1
    cmd = "netperf %s %d flow" % (test_type, flow)

    # 打印表头
    print_task_name(cmd)

    for i in range(1, many + 1):
        cmd = "netperf %s %d flow" % (test_type, flow)
        print_log("Round: %d\tcmd=%s" % (i, cmd))
        tcp_rr = 0

        #临时文件
        tmp_prefix = "/tmp/netperf_rr_"
        cmd = "rm -f %s* 2>&1 > /dev/null" % (tmp_prefix)
        os.system(cmd)

        for j in range(1, flow+1):
            port = base_port + j -1
            cmd = "netperf -H %s -p %d -t %s -l %d -- -r %d 2>&1 > %s%d.log &" \
                   % (serverip, port, test_type, test_time, byte, tmp_prefix, port)
            os.system(cmd)

        #获取结果
        time.sleep(5 + test_time)
        for j in range(1, flow+1):
            port = base_port + j - 1
            tmp_file = "%s%d.log" % (tmp_prefix, port)
            f = open(tmp_file)
            tmp_ret = f.read().splitlines()
            rr_str = tmp_ret[-2].strip().split(" ")[-1]
            tcp_rr += float(rr_str)
            f.close()

        #数据格式化
        tcp_rr = round(tcp_rr)
        ret_value.append((tcp_rr,))

        #清理临时文件
        time.sleep(2)
        cmd = "rm -f %s* 2>&1 > /dev/null" % (tmp_prefix)
        os.system(cmd)

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

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
    tcp_crr = -1
    cmd = "netperf %s %d flow" % (type, flow)

    # 打印表头
    print_task_name(cmd)

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

    # 局部变量
    ret_value = []

    #打印表头
    cmd = "memcached %d flow" % flow
    print_task_name(cmd)

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

        #多次测试之间停留10s
        if i < many:
            time.sleep(10)

    return ret_value


#函数功能，测试c1000k并发连接数
def run_multi_user_c1000k(serverip, flow=2, base_port=11000, many=1):
    """
    #函数功能，测试c1000k并发连接数
    :param serverip:
    :param flow:
    :param base_port:
    :param many:
    """

    #局部变量
    ret_value = []
    cmd = "c1000k %d flow test" % flow

    # 打印表头
    print_task_name(cmd)

    for i in range(1, many + 1):
        print_log("Round: %d\tcmd=%s" % (i, cmd))

        #执行c1000k测试
        for j in range(1, flow + 1):
            port = base_port + (j-1)*2000
            cmd = "%s/client %s %d 2>&1 > /dev/null &" % (os.getcwd(), serverip, port)
            os.system(cmd)
            time.sleep(10)

        #获取连接数
        old = new = 0
        max_conn = 0
        same_time = 0

        #采集连接数
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

            #获取最大连接数
            if new > max_conn:
                max_conn = new

            #数据与上次相比，变化了没有
            if new == old:
                same_time += 1
            else:
                same_time = 0

            #连续N次连接数不更新，认为结束，退出采集
            if same_time > 10:
                break

            #进入下一次采集
            old = new
            time.sleep(10)

        #关闭client程序
        process_name = "%s/client" % os.getcwd()
        print "our time is short!"
        print process_name
        shutdown_process(process_name)

        #结果处理
        ret_value.append((max_conn,))

        # 2次测试程序间隔600s以上,让计算节点tcp老化
        if i < many:
            time.sleep(700)

    return ret_value





############  main函数入口  ############
def main():
    host = "192.168.1.74"
    off()

    TEST_TIME = 120
    TEST_MANY = 5

    ret = run_ping(host, count=60, many=TEST_MANY)
    print_log(ret)

    ret = run_qperf(host, test_time=TEST_TIME, many=TEST_MANY)
    print_log(ret)

    netperf = ["TCP_STREAM", "udp_stream", "tcp_rr", "tcp_crr", "udp_rr"]
    for i in netperf:
        ret = run_one_netperf(host, test_type=i, test_time=TEST_TIME, many=TEST_MANY)
        print_log(ret)

    ret = run_one_ab(host, total_count=10000, many=TEST_MANY)
    print_log(ret)

    ret = run_one_memcached(host, test_time=TEST_TIME, many=TEST_MANY)
    print_log(ret)

    ret = run_scp_speed(host, size=1024, many=TEST_MANY)
    print_log(ret)

    ret = run_meinian_udp_check(host, check_num=20, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_netperf_send_bandwidth(host, test_time=TEST_TIME, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_tcp_rr(host, flow=16, test_time=TEST_TIME, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_tcp_crr(host, flow=1, test_time=TEST_TIME, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_c1000k(host, flow=1, many=TEST_MANY)
    print_log(ret)

    ret = run_multi_user_memcached(host, test_time=TEST_TIME, many=TEST_MANY)
    print_log(ret)









if __name__ == '__main__':
    main()
    print_log("work complete! 搞完了")
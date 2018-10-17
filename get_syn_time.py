#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author：caoguozhi
# date: 2018-10-15
# version: v0.2
# 程序功能：输入tcpdump抓下来的pcap报文，分析SYN到SYN_ACK之间的时间差别，用于分析TCP新建收个报文花费时间。
# 程序用法：python 程序名 <xxx.pcap> [count]
# 参数1：xxx.pcap必选,tcpdump的抓包文件  count：总统统计多少条TCP流,默认1000


import os
import sys
import time
import re


# 全局变量，PCAP_FILE：输入文件  OUTPUT_FILE：转换后txt文件  PARSE_COUNT：统计多少条  STEP:当前步骤
PCAP_FILE = ""
OUTPUT_FILE = ""
PARSE_COUNT = 1000
STEP = 1

# syn时间结果列表,syn_pair_list:已匹配的流列表  syn_list：纯syn列表  syn_ack_list:纯syn_ack列表
syn_pair_list = []
syn_list = []
syn_ack_list = []


# 函数功能：打印步骤名称,msg：消息  new：是否本行打印结束
def print_step(msg="", new=False):
    """
    # 函数功能：打印步骤名称
    :param msg: 打印内容
    :param new: 是否本行打印结束
    """

    global STEP
    if new == True:
        print msg
        STEP += 1
    else:
        print "step: {}\t{:.<50s}".format(STEP,msg),


# 函数功能:pcap格式转换为txt文本格式
def pcap_to_txt(pcap_file=PCAP_FILE):
    """
    #函数功能:pcap格式转换为txt文本格式
    :param pcap_file: 待转换的pcap文件
    """

    global OUTPUT_FILE

    # 清除文件
    cmd = "rm -f %s 2>/dev/null 1>/dev/null" % OUTPUT_FILE
    os.system(cmd)

    print_step("convert pcap to text file")
    # 转换pcap to txt
    cmd = "tcpdump -r %s -nne > %s 2>/dev/null" % (pcap_file, OUTPUT_FILE)
    ret = os.system(cmd)

    # 检查是否转换成功，非0则失败
    if ret != 0:
        print "转换失败，exit..."
        cmd = "rm -f $s 2>/dev/null 1>/dev/null" % OUTPUT_FILE
        os.system(cmd)
        exit(-1)

    print_step("ok", new=True)


# 函数功能：解析syn，syn+ack时间间隔
def parse_tcp_syn_time(src_file=OUTPUT_FILE, max_count=-1):
    """
    #函数功能：解析syn，syn+ack时间间隔
    :param src_file: 转换过的txt格式抓包文件
    :param max_count: 解析多少个syn，-1就是不限制
    """

    pcap_context = ""
    global syn_pair_list
    global syn_list
    global syn_ack_list

    print_step("read pcap text context")
    # 读取文本
    try:
        f = open(OUTPUT_FILE, 'r')
        pcap_context = f.read().splitlines()
        f.close()
    except:
        print "read pcap file failed,file=%s" % OUTPUT_FILE
        exit(-1)

    # 开始解析
    print_step("ok", new=True)
    print_step("parse syn packet")
    # 获取所有的syn流，加入syn列表
    index = cur_count = 0
    for i in pcap_context:
        index += 1

        # 判断是否为SYN
        if "[S]" in i:
            # 解析报文字段时间，src_ip,dst_ip,seq
            tmp_str = i.split(" ")
            t = tmp_str[0]

            # 正则匹配，抓x.x.x.x.port形式的字符串
            ret = re.findall(r"\b(?:[0-9]{1,3}\.){4}[0-9]{1,5}\b", i)
            if ret:
                src_ip = ret[0]
                dst_ip = ret[1]

            # seq
            pos1 = i.find("seq")
            pos2 = i.find(",", pos1)
            seq = int(i[pos1+4:pos2])

            syn_flow = (index, t, src_ip, dst_ip, seq,)
            syn_list.append(syn_flow)

        # 判断是否为SYN+ACK
        elif "[S.]" in i:
            # 解析报文字段 时间，src_ip,dst_ip,seq
            tmp_str = i.split(" ")
            t = tmp_str[0]

            ret = re.findall(r"\b(?:[0-9]{1,3}\.){4}[0-9]{1,5}\b", i)
            if ret:
                src_ip = ret[0]
                dst_ip = ret[1]

            # ack
            pos1 = i.find("ack")
            pos2 = i.find(",", pos1)
            ack = int(i[pos1+4:pos2])

            syn_ack_flow = (index, t, src_ip, dst_ip, ack,)
            syn_ack_list.append(syn_ack_flow)

    print_step("ok", new=True)
    print_step("match tcp flow")
    # 匹配完整的流，加入pair列表
    index = cur_count = 0

    for i in syn_list:
        syn_index = i[0]
        syn_time = i[1]
        syn_src_ip = i[2]
        syn_dst_ip = i[3]
        syn_seq = i[4]

        if (max_count != -1) and (cur_count >= max_count):
            break

        for j in syn_ack_list:
            syn_ack_index = j[0]
            syn_ack_time = j[1]
            syn_ack_src_ip = j[2]
            syn_ack_dst_ip = j[3]
            syn_ack_ack = j[4]

            # 判断是否相关联
            if syn_ack_index > syn_index and \
                syn_ack_time > syn_time and \
                syn_ack_src_ip == syn_dst_ip and \
                syn_ack_dst_ip == syn_src_ip and \
                syn_ack_ack == syn_seq+1:

                cur_count += 1
                # 找到了完整TCP流，最后一个字符0，预先插入时间差占位
                tcp_flow = (syn_index, syn_time, syn_src_ip, syn_dst_ip, syn_seq,
                            syn_ack_index, syn_ack_time, syn_ack_src_ip, syn_ack_dst_ip, syn_ack_ack, 0,)

                syn_pair_list.append(tcp_flow)

    print_step("ok", new=True)
    print_step("calculate syn time")

    # 当前索引位置
    cur_index = 0
    for i in syn_pair_list:
        # 字符串切割,转换成sec和us列表
        syn_time = i[1]
        syn_ack_time = i[6]
        syn_time_str = syn_time.split(".")
        syn_ack_time_str = syn_ack_time.split(".")
        syn_time_d1 = syn_time_str[0]
        syn_time_d2 = syn_time_str[1]
        syn_ack_time_d1 = syn_ack_time_str[0]
        syn_ack_time_d2 = syn_ack_time_str[1]

        # 转换成时间格式,分别计算sec和us
        t1_sec = time.mktime(time.strptime(syn_time_d1, "%H:%M:%S"))
        t2_sec = time.mktime(time.strptime(syn_ack_time_d1, "%H:%M:%S"))
        t1_us = int(syn_time_d2)
        t2_us = int(syn_ack_time_d2)

        # 计算时间差
        time_diff = (t2_sec-t1_sec)*1000*1000 + (t2_us-t1_us)
        tmp_time_list = list(i)
        tmp_time_list[-1] = time_diff
        syn_pair_list[cur_index] = tuple(tmp_time_list)

        cur_index += 1

    print_step("ok", new=True)

# 函数功能：打印时间消耗列表
def print_syn_time_used():
    """
    #函数功能：打印时间消耗列表
    """

    global syn_pair_list
    min_time = -1
    max_time = -1

    # 打印表头
    header_format = "%-7s %-7s  %s %s --> %s %s"
    seperate_format = "-"*70
    data_format = "%-7d %-7d  [%d] %s --> [%d] %s"

    print
    print(header_format % ("No.", "us", "[pkt_id1]", "src_ip", "[pkt_id2]", "dst_ip"))
    print seperate_format

    cur_index = 0
    avg_time = 0
    for i in syn_pair_list:
        avg_time += i[-1]
        cur_index += 1

        if min_time == -1:
            min_time = i[-1]

        if max_time == -1:
            max_time = i[-1]

        if i[-1] < min_time:
            min_time = i[-1]

        if i[-1] > max_time:
            max_time = i[-1]

        print(data_format % (cur_index, i[-1], i[0], i[2], i[5], i[3]))

    print seperate_format
    print "avg_time:%d us  total_count:%d  min_time:%d us  max_time:%d us" % (avg_time/cur_index, cur_index, min_time, max_time)
    print seperate_format


# 函数功能：main入口函数
def main():
    pcap_to_txt(PCAP_FILE)
    parse_tcp_syn_time(OUTPUT_FILE, PARSE_COUNT)
    print_syn_time_used()


if __name__ == '__main__':
    # 参数校验
    if len(sys.argv) <= 1:
        print "你pcap文件名都不给，我怎么知道分析啥...\nUsage: python %s file" % sys.argv[0]
        exit(-1)
    elif len(sys.argv) == 2:
        PCAP_FILE = sys.argv[1]
        OUTPUT_FILE = "%s.txt" % PCAP_FILE
    elif len(sys.argv) == 3:
        PCAP_FILE = sys.argv[1]
        OUTPUT_FILE = "%s.txt" % PCAP_FILE
        tmp_count = sys.argv[2]
        try:
            tmp_count = int(tmp_count)
            PARSE_COUNT = tmp_count
        except ValueError:
            pass

    # 调用主函数
    main()

    # 清理临时文件
    cmd = "rm -f %s 2>/dev/null 1>/dev/null" % OUTPUT_FILE
    os.system(cmd)
    print "work complete, all done!"

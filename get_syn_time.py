#!/usr/bin/env python
# -*- coding:utf-8 -*-


import os
import datetime
import time
import re


#全局变量
PCAP_FILE = "./nginx.pcap"
OUTPUT_FILE = PCAP_FILE.replace("pcap", "txt")


#函数功能:pcap格式转换为txt文本格式
def pcap_to_txt(pcap_file = PCAP_FILE):
    """
    #函数功能:pcap格式转换为txt文本格式
    :param pcap_file: 待转换的pcap文件
    """

    global OUTPUT_FILE

    #清除文件
    cmd = "rm -f %s 2>/dev/null 1>/dev/null" % OUTPUT_FILE
    os.system(cmd)

    #转换pcap to txt
    cmd = "tcpdump -r %s -nne > %s 2>/dev/null" % (pcap_file, OUTPUT_FILE)
    ret = os.system(cmd)

    #检查是否转换成功，非0则失败
    if ret != 0:
        print "转换失败，exit。。。"
        exit(-1)

    print "ok,转换完成"


#函数功能：解析syn，syn+ack时间间隔
def parse_tcp_syn_time(src_file = OUTPUT_FILE, max_count = -1):
    """
    #函数功能：解析syn，syn+ack时间间隔
    :param src_file: 转换过的txt格式抓包文件
    :param count: 解析多少个syn，-1就是不限制
    """

    #syn时间结果列表，一条流一个字典格式
    syn_pair_list = []
    syn_list = []
    syn_ack_list = []
    pcap_context = ""

    #读取文本
    try:
        f = open(OUTPUT_FILE, 'r')
        pcap_context = f.read().splitlines()
        f.close()
    except:
        print "读取文件失败 file=%s" % OUTPUT_FILE
        exit(-1)

    #开始解析
    print "开始解析TCP SYN时间"

    #获取所有的syn流，加入syn列表
    index = cur_count = 0
    for i in pcap_context:
        index += 1
        #判断是否为SYN
        if "[S]" in i:
            # cur_count += 1
            # if cur_count > 10:
            #     break

            #解析报文字段时间，src_ip,dst_ip,seq
            tmp_str = i.split(" ")
            t = tmp_str[0]

            ret = re.findall(r"\b(?:[0-9]{1,3}\.){4}[0-9]{1,5}\b", i)
            if ret:
                src_ip = ret[0]
                dst_ip = ret[1]

            #seq
            pos1 = i.find("seq")
            pos2 = i.find(",", pos1)
            seq = int(i[pos1+4:pos2])

            syn_flow = (index, t, src_ip, dst_ip, seq)
            syn_list.append(syn_flow)

            #print "No.%d\tsrc_ip=%s\tdst_ip=%s\tseq=%d" % (index, src_ip, dst_ip, seq)
            #print "No.%d\t%s" % (index, i)
            #print
    print "SYN解析完成"

    print "开始解析SYN+ACK"
    #获取syn_ack流，加入syn_ack列表
    index = cur_count = 0
    for i in pcap_context:
        index += 1
        #判断是否为SYN+ACK
        if "[S.]" in i:
            # cur_count += 1
            # if cur_count > 10:
            #     break

            #解析报文字段 时间，src_ip,dst_ip,seq
            tmp_str = i.split(" ")
            t = tmp_str[0]

            ret = re.findall(r"\b(?:[0-9]{1,3}\.){4}[0-9]{1,5}\b", i)
            if ret:
                src_ip = ret[0]
                dst_ip = ret[1]

            #ack
            pos1 = i.find("ack")
            pos2 = i.find(",", pos1)
            ack = int(i[pos1+4:pos2])

            syn_ack_flow = (index, t, src_ip, dst_ip, ack)
            syn_ack_list.append(syn_ack_flow)

    print "SYN+ACK解析完成"

    print "开始匹配"
    #匹配完整的流，加入pair列表
    index = cur_count = 0
    b_full = False

    for i in syn_list:
        syn_index = i[0]
        syn_time = i[1]
        syn_src_ip = i[2]
        syn_dst_ip = i[3]
        syn_seq = i[4]

        if b_full:
            break

        for j in syn_ack_list:
            syn_ack_index = j[0]
            syn_ack_time = j[1]
            syn_ack_src_ip = j[2]
            syn_ack_dst_ip = j[3]
            syn_ack_ack = j[4]

            #判断是否相关联
            if syn_ack_index > syn_index and \
                syn_ack_time > syn_time and \
                syn_ack_src_ip == syn_dst_ip and \
                syn_ack_dst_ip == syn_src_ip and \
                syn_ack_ack == syn_seq+1:

                print "找到1个逗比"
                #找到了完整TCP流
                tcp_flow = (syn_index, syn_time, syn_src_ip, syn_dst_ip, syn_seq,
                            syn_ack_index, syn_ack_time, syn_ack_src_ip, syn_ack_dst_ip, syn_ack_ack)

                syn_pair_list.append(tcp_flow)

                #个数满了
                cur_count += 1
                if (max_count != -1) and (cur_count>max_count):
                    b_full = True
                    break

    print "匹配完成"
    cur_count = 0
    for i in syn_pair_list:
        cur_count += 1
        if cur_count > 100 :
            break

        print i


#函数功能：main入口函数
def main():
    pcap_to_txt()
    parse_tcp_syn_time(OUTPUT_FILE, 10)


if __name__ == '__main__':
    main()
    print "work complete,全部搞完了!"
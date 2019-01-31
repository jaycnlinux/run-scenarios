#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = 'chengxiang'


import os
import sys
import copy
import math


######## 全局变量
# 分析类型：接收PPS，发送PPS，接收带宽，发送带宽
qos_type_list = ['rx_pps', 'tx_pps', 'rx_kbps', 'tx_kbps']
qos_type = qos_type_list[0]
sar_file = ''
percent_threshold = 0.04
rx_pps_list = []
tx_pps_list = []
rx_kbps_list = []
tx_kbps_list = []


# 打印使用方法
def usage():
    print '''%s file method percent
--------------------------------
file            sar file
method          rx_pps|tx_pps|rx_kbps|tx_kbps
percent         between 0 and 100'''
    exit(1)


# 解析参数
def parse_args():
    global sar_file
    global qos_type
    global qos_type_list
    global percent_threshold
    arg_num = len(sys.argv)
    if arg_num < 3:
        print 'arg num < 3,exit 1'
        usage()
    elif arg_num == 3:
        sar_file = sys.argv[1]
        qos_type = str(sys.argv[2]).lower()
    elif arg_num == 4:
        sar_file = sys.argv[1]
        qos_type = str(sys.argv[2]).lower()
        percent_threshold = str(sys.argv[3])
        if percent_threshold.isdigit():
            percent_threshold = int(percent_threshold)
        else:
            print 'percent not digital,exit 1'
            usage()
    else:
        print 'arg numbers > 4,exit 1'
        usage()

    # 检查参数有效性
    if not os.path.isfile(sar_file):
        print 'sar file not exist,exit 1'
        usage()
    if qos_type not in qos_type_list:
        usage()
    if percent_threshold < 0 or percent_threshold > 1:
        print 'percent invalid,exit 1'
        usage()

    # 调试输出
    #print 'sar_file=%s\tpercent=%d' % (sar_file, percent_threshold)

# 设置响应列表值
def set_value():
    f = open(sar_file, 'r')
    while True:
        ret = f.readline()
        if ret == '':
            break
        elif 'average' in ret.lower():
            continue
        ret = ret.split()
        rx_pps_list.append(float(ret[3]))
        tx_pps_list.append(float(ret[4]))
        rx_kbps_list.append(float(ret[5]))
        tx_kbps_list.append(float(ret[6]))
    f.close()


# 获取百分比函数
def get_percentail(data, percent):
    def get_data(data, percent):
        count = len(data)
        sum = (count-1) * percent # 计算
        pos_i = int(math.floor(sum))
        pos_j = sum - pos_i
        # print 'sum=%f\tpos_i=%d\tpos_j=%f' % (sum,pos_i,pos_j)
        percent_data = (1-pos_j)*data[pos_i] + pos_j*data[pos_i+1]
        return percent_data

    qos1 = get_data(data, percent)
    qos2 = get_data(data, 1-percent)
    if qos1 < qos2:
        return qos1, qos2
    else:
        return qos2, qos1

# 计算波动
def get_net_qos():
    global qos_type
    global qos_type_list
    global percent_threshold

    if qos_type == qos_type_list[0]:
        rx_pps_new = copy.deepcopy(rx_pps_list)
        rx_pps_new.sort()
        min,max = get_percentail(rx_pps_new, percent_threshold)
        print '%d\tmin=%f,max=%f' % (percent_threshold, min, max)
        pass
    elif qos_type == qos_type_list[1]:
        tx_pps_new = copy.deepcopy(tx_pps_list)
        tx_pps_new.sort()
        pass
    elif qos_type == qos_type_list[2]:
        rx_kbps_new = copy.deepcopy(rx_kbps_list)
        rx_kbps_new.sort()
        pass
    elif qos_type == qos_type_list[3]:
        tx_kbps_new = copy.deepcopy(tx_kbps_list)
        tx_kbps_new.sort()
        pass
    else:
        print 'method not find,exit'


# 入口main主函数
def main():
    parse_args()
    set_value()
    get_net_qos()
    print 'all done'


if __name__ == '__main__':
    main()

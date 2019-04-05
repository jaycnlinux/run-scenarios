#!/usr/bin/python
# -*- encoding: utf-8 -*-
# __author__ = 'chengxiang'


import os, sys
import re
import copy
import time
import numpy


BASE_DIR = 'C:\\Users\\c00406647\\Desktop\\aws-qos-data\\'
file_dict = {'bw': 'bw.txt', 'qperf': 'qperf.txt', 'ping': 'ping.txt', 'memcached': 'memcached.txt'}
RESULT_DIR = 'new'
RESULT_DATA = []
TYPE_LIST = dict()


def check_name(func):
    """ 文件判断装饰器 """
    def wrapper(*args, **kwargs):
        if len(args) == 0 and len(kwargs) == 0:
            print '文件名都没有，搞个毛啊'
        else:
            # print 'call %s, file=%s' % (func.__name__ , args)
            return func(*args, **kwargs)
    return wrapper


@check_name
def process_sar(filename=''):
    # s_name = os.path.basename(filename)
    # cur_dir = os.path.basename(os.path.dirname(filename))
    r_sar = '\d{2}(?::\d+)+\s*(?:AM|PM)\s+(?:ens|eth)\d+'
    r_begin = 'sar on send'
    b_begin = False
    r_end = 'Average:'
    ret = []
    with open(filename, 'r') as f:
        for line in f:
            if re.search(r_begin, line):
                b_begin = True
            if b_begin and re.search(r_sar, line):
                # 匹配到了sar
                bw_str = line.split()[-1]
                bw = round(float(bw_str), 2)
                ret.append(bw)
            if re.search(r_end, line):
                b_begin = False
    return ret


@check_name
def process_qperf(filename=''):
    r_qperf = '^latency[\W\w]*'
    r_begin = '^udp_lat:[\w\W]*'
    r_end = 'msg_size'
    ret = []
    b_begin = False
    with open(filename, 'r') as f:
        for line in f:
            if re.search(r_begin, line):
                b_begin = True
            if b_begin and re.search(r_qperf, line):
                qperf_str = line.split()
                qperf = round(float(qperf_str[2]), 2)
                unit = qperf_str[-1]
                if 'ms' in unit.lower():
                    qperf = qperf * 1000.
                elif 'sec' in unit.lower():
                    qperf = qperf * 1000. * 1000.
                ret.append(qperf)
            if re.search(r_end, line):
                b_begin = False
    return ret


@check_name
def process_ping(filename=''):
    r_ping = '^\d+\.\d+$'
    r_begin = 'ping: fetch_data'
    r_end = '^\s+$'
    ret = []
    b_begin = False
    with open(filename, 'r') as f:
        for line in f:
            if re.search(r_begin, line):
                b_begin = True
            if b_begin and re.search(r_ping, line):
                ping_str = line.split()
                ping = round(float(ping_str[0]), 3)
                ret.append(ping)
            if re.search(r_end, line):
                b_begin = False
    return ret


@check_name
def process_memcache(filename=''):
    r_memcache = 'Run[\w\W]*Ops[\w\W]*TPS:\s*\d+'
    r_begin = 'get_misses:\s\d+'
    r_end = '^\s+$'
    ret = []
    b_begin = False
    with open(filename, 'r') as f:
        for line in f:
            if re.search(r_begin, line):
                b_begin = True
            if b_begin and re.search(r_memcache, line):
                memcach_str = re.findall('TPS:\s+\d+', line)[0].split()
                memcache = int(memcach_str[-1])
                ret.append(memcache)
            if re.search(r_end, line):
                b_begin = False
    return ret


def write_data_to_file(filename, datalist, datatype, record):
    if not filename or not datalist or not record:
        return
    # 写入文件
    with open(filename, 'a+') as f:
        for item in datalist:
            str_format = [record['vender'],record['region'],record['time'],datatype,'vm%s' % record['vm'],str(item)]
            context = ','.join(str_format)
            f.write(context + '\n')


def write_data_to_global(flavor, datalist, datatype, record):
    ele = dict()
    ele['flavor'] = flavor
    ele['vender'] = record['vender']
    ele['region'] = record['region']
    ele['vm'] = record['vm']
    ele['time'] = record['time']
    # 加入全局存储
    ele['type'] = datatype
    ele['data'] = copy.deepcopy(datalist)
    RESULT_DATA.append(ele)


def process_data(basedir=''):
    if not basedir:
        return
    all_file = os.listdir(basedir)
    file_list = dict()
    global RESULT_DATA
    global TYPE_LIST
    seg_index = dict()
    # generate file dict
    for f in all_file:
        if os.path.isfile(os.path.join(basedir, f)):
            ret = f.split('-')
            ftime = ret[0]
            vender = ret[1]
            region = ret[2]
            flavor = vender + '-' + ret[3] + '-' + ret[4]
            vm = ret[5].split('.')[0]
            ele = dict()
            ele['vender'] = vender
            ele['region'] = region
            ele['time'] = ftime
            ele['file'] = os.path.join(basedir, f)
            ele['vm'] = 'vm%s' % vm
            ele['isread'] = False
            if flavor not in file_list.keys():
                file_list[flavor] = []
            file_list[flavor].append(ele)
    # generate data
    for k,v in file_list.items():
        # 一个flavor的几个文件
        flavor_file = os.path.join(BASE_DIR, RESULT_DIR, '%s.csv' % k)
        # 如果结果文件夹不存在，则创建
        if not os.path.isdir(os.path.dirname(flavor_file)):
            os.makedirs(os.path.dirname(flavor_file))
        # 如果文件不存在，创建则创建
        if not os.path.isfile(flavor_file):
            with open(flavor_file, 'w') as f:
                context = 'vender,region,time,type,vm,data'
                f.write(context+'\n')
        # 3组虚拟机
        for record in v:
            ret_sar = process_sar(record['file'])
            ret_qperf = process_qperf(record['file'])
            ret_ping = process_ping(record['file'])
            ret_memcache = process_memcache(record['file'])
            # print 'process flavor: %s    %s' % (k, record['file'])
            # save to result file
            write_data_to_file(flavor_file, ret_sar, 'tcp-bw', record)
            write_data_to_file(flavor_file, ret_qperf, 'qperf-udp', record)
            write_data_to_file(flavor_file, ret_ping, 'ping', record)
            write_data_to_file(flavor_file, ret_memcache, 'memcache', record)
            # copy to global data
            write_data_to_global(flavor=k, datalist=ret_sar, datatype='tcp-bw', record=record)
            write_data_to_global(flavor=k, datalist=ret_qperf, datatype='qperf-udp', record=record)
            write_data_to_global(flavor=k, datalist=ret_ping, datatype='ping', record=record)
            write_data_to_global(flavor=k, datalist=ret_memcache, datatype='memcache', record=record)
    # generate index
    for record in RESULT_DATA:
        vender = record['vender']
        region = record['region']
        flavor = record['flavor']
        str_time = record['time']
        vm = record['vm']
        if vender not in TYPE_LIST.keys():
            TYPE_LIST[vender] = {'region': [region], 'flavor': [flavor], 'time': [str_time], 'vm': [vm]}
        for k,v in TYPE_LIST.items():
            if vender == k and region not in v['region']:
                v['region'].append(region)
            if vender == k and flavor not in v['flavor']:
                v['flavor'].append(flavor)
            if vender == k and str_time not in v['time']:
                v['time'].append(str_time)
            if vender == k and vm not in v['vm']:
                v['vm'].append(vm)


def generate_data_from_log():
    for dirname in os.listdir(BASE_DIR):
        cur_dir = os.path.join(BASE_DIR, dirname)
        # 排除目标文件夹
        if dirname != RESULT_DIR:
            process_data(os.path.join(BASE_DIR, cur_dir))


def compute_percent_and_avg(datalist):
    """ 计算平均值，p99波动、p100波动,pavg波动平均值，pdev波动均方差，注意返回结果已经*100了 """
    new_data = copy.deepcopy(datalist)
    avg = numpy.average(new_data)
    diff = []
    for i in new_data:
        p = abs(i-avg)*100./avg
        diff.append(p)
    p99 = numpy.percentile(diff, 99)
    p100 = numpy.percentile(diff, 100)
    pavg = numpy.average(diff)
    pdev = numpy.std(diff, ddof=1)
    # number format
    avg = round(avg, 3)
    p99 = round(p99, 1)
    p100 = round(p100, 1)
    pavg = round(pavg, 1)
    pdev = int(pdev)
    return avg, p99, p100, pavg, pdev


def compute_data_by_site():
    """ 站点间数据比较 """
    csv_file = os.path.join(BASE_DIR, RESULT_DIR, 'site.csv')
    with open(csv_file, 'a') as f:
        f.write('vender,region,flavor,type,p99,p100,pavg,pdev,avg\n')
    # csv表格存储
    sum_bw = []
    sum_qperf = []
    sum_ping = []
    sum_memcache = []
    for vender in TYPE_LIST.keys():
        # 每个flavor单独比较
        for flavor in TYPE_LIST[vender]['flavor']:
            # 依次轮询region
            for region in TYPE_LIST[vender]['region']:
                bw_data = []
                qperf_data = []
                ping_data = []
                memcache_data = []
                for record in RESULT_DATA:
                    # get_bw
                    if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and 'tcp-bw' == record['type']:
                        bw_data.extend(record['data'])
                    if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and 'qperf-udp' == record['type']:
                        qperf_data.extend(record['data'])
                    if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and 'ping' == record['type']:
                        ping_data.extend(record['data'])
                    if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and 'memcache' == record['type']:
                        memcache_data.extend(record['data'])
                # 算分vender,region,flavor,type,p99,p100,pavg,pdev,avg
                msg_format = '{0},{1},{2},{3},{4}%,{5}%,{6}%,{7},{8}'
                if bw_data:
                    avg,p99,p100,pdev,pavg = compute_percent_and_avg(bw_data)
                    msg = msg_format.format(vender, region, flavor, 'tcp-bw', p99, p100, pavg, pdev, int(avg))
                    ele = [vender, region, flavor, 'tcp-bw', p99, p100, pavg, pdev, int(avg)]
                    sum_bw.append(ele)
                    with open(csv_file, 'a') as f:
                        f.write(msg+'\n')
                    print msg
                if qperf_data:
                    avg,p99,p100,pavg,pdev = compute_percent_and_avg(qperf_data)
                    msg = msg_format.format(vender, region, flavor, 'qperf', p99, p100, pavg, pdev, round(avg, 1))
                    ele = [vender, region, flavor, 'tcp-bw', p99, p100, pavg, pdev, int(avg)]
                    sum_qperf.append(ele)
                    with open(csv_file, 'a') as f:
                        f.write(msg+'\n')
                    print msg
                if ping_data:
                    avg,p99,p100,pavg,pdev = compute_percent_and_avg(ping_data)
                    msg = msg_format.format(vender, region, flavor, 'ping', p99, p100, pavg, pdev, round(avg, 2))
                    ele = [vender, region, flavor, 'tcp-bw', p99, p100, pavg, pdev, int(avg)]
                    sum_ping.append(ele)
                    with open(csv_file, 'a') as f:
                        f.write(msg+'\n')
                    print msg
                if memcache_data:
                    avg,p99,p100,pavg,pdev = compute_percent_and_avg(memcache_data)
                    msg = msg_format.format(vender, region, flavor, 'memcache', p99, p100, pavg, pdev, int(avg))
                    ele = [vender, region, flavor, 'tcp-bw', p99, p100, pavg, pdev, int(avg)]
                    sum_memcache.append(ele)
                    with open(csv_file, 'a') as f:
                        f.write(msg+'\n')
                    print msg
    # 整理成表格方式
    type_list = ['tcp-bw', 'qperf-udp', 'ping', 'memcache']
    # 开始匹配
    for vender in TYPE_LIST.keys():
        flavor_list = TYPE_LIST[vender]['flavor']
        region_list = TYPE_LIST[vender]['region']
        for flavor in flavor_list:
            msg =  '===================== flavor %s' % flavor
            print msg
            with open('site0.csv', 'a') as f:
                f.write(msg+'\n')
            for ttype in type_list:
                v = dict()
                for region in region_list:
                    v[region] = []
                    for record in sum_qperf:
                        t_vender = record[0]
                        t_region = record[1]
                        t_flavor = record[2]
                        t_type = record[3]
                        t_p99 = record[4]
                        t_p100 = record[5]
                        t_pavg = record[6]
                        t_pdev = record[7]
                        t_avg = record[8]
                        if t_vender == vender and t_region == region and t_flavor == flavor and t_type == ttype:
                            v[region].append(t_p99)
                            v[region].append(t_p100)
                            v[region].append(t_pavg)
                            v[region].append(t_pdev)
                            v[region].append(t_avg)
                # 轮询了所有的region，得到一行记录
                msg = ''
                for i in range(5):  # 5个指标
                    for region in region_list:
                        record = v[region]
                        try:
                            msg += str(record[i])
                        except Exception as e:
                            msg += '-'
                        msg += ','
                msg = msg.rstrip(',')
                with open('site0.csv', 'a+') as f:
                    f.write(msg+'\n')



def compute_data_by_vm():
    """ 虚拟机间比较 """
    csv_file = os.path.join(BASE_DIR, RESULT_DIR, 'vm.csv')
    with open(csv_file, 'a') as f:
        f.write('vender,region,vm,flavor,type,p99,p100,pavg,pdev,avg\n')
    for vender in TYPE_LIST.keys():
        # 每个flavor单独比较
        for flavor in TYPE_LIST[vender]['flavor']:
            # 依次轮询region
            for region in TYPE_LIST[vender]['region']:
                bw_data = []
                qperf_data = []
                ping_data = []
                memcache_data = []
                for vm in TYPE_LIST[vender]['vm']:
                    for record in RESULT_DATA:
                        # get_bw
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and vm == record['vm'] and 'tcp-bw' == record['type']:
                            bw_data.extend(record['data'])
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and vm == record['vm'] and 'qperf-udp' == record['type']:
                            qperf_data.extend(record['data'])
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and vm == record['vm'] and 'ping' == record['type']:
                            ping_data.extend(record['data'])
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and vm == record['vm'] and 'memcache' == record['type']:
                            memcache_data.extend(record['data'])
                    # 算分vender,region,vm,flavor,type,p99,p100,pavg,pdev,avg
                    msg_format = '{0},{1},{2},{3},{4},{5}%,{6}%,{7}%,{8},{9}'
                    if bw_data:
                        avg,p99,p100,pdev,pavg = compute_percent_and_avg(bw_data)
                        msg = msg_format.format(vender, region, vm, flavor, 'tcp-bw', p99, p100, pavg, pdev, int(avg))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg
                    if qperf_data:
                        avg,p99,p100,pavg,pdev = compute_percent_and_avg(qperf_data)
                        msg = msg_format.format(vender, region, vm, flavor, 'qperf', p99, p100, pavg, pdev, round(avg, 1))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg
                    if ping_data:
                        avg,p99,p100,pavg,pdev = compute_percent_and_avg(ping_data)
                        msg = msg_format.format(vender, region, vm, flavor, 'ping', p99, p100, pavg, pdev, round(avg, 2))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg
                    if memcache_data:
                        avg,p99,p100,pavg,pdev = compute_percent_and_avg(memcache_data)
                        msg = msg_format.format(vender, region, vm, flavor, 'memcache', p99, p100, pavg, pdev, int(avg))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg


def compute_data_by_time():
    """ 时间维度比较 """
    csv_file = os.path.join(BASE_DIR, RESULT_DIR, 'time.csv')
    with open(csv_file, 'a') as f:
        f.write('vender,region,time,flavor,type,p99,p100,pavg,pdev,avg\n')
    for vender in TYPE_LIST.keys():
        # 每个flavor单独比较
        for flavor in TYPE_LIST[vender]['flavor']:
            # 依次轮询region
            for region in TYPE_LIST[vender]['region']:
                bw_data = []
                qperf_data = []
                ping_data = []
                memcache_data = []
                for str_time in TYPE_LIST[vender]['time']:
                    for record in RESULT_DATA:
                        # get_bw
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and str_time == record['time'] and 'tcp-bw' == record['type']:
                            bw_data.extend(record['data'])
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and str_time == record['time'] and 'qperf-udp' == record['type']:
                            qperf_data.extend(record['data'])
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and str_time == record['time'] and 'ping' == record['type']:
                            ping_data.extend(record['data'])
                        if vender == record['vender'] and flavor == record['flavor'] and region == record['region'] and str_time == record['time'] and 'memcache' == record['type']:
                            memcache_data.extend(record['data'])
                    # 算分vender,region,time,flavor,type,p99,p100,pavg,pstd,avg
                    msg_format = '{0},{1},{2},{3},{4},{5}%,{6}%,{7}%,{8},{9}'
                    if bw_data:
                        avg,p99,p100,pavg,pdev = compute_percent_and_avg(bw_data)
                        msg = msg_format.format(vender, region, str_time, flavor, 'tcp-bw', p99, p100, pavg, pdev, int(avg))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg
                    if qperf_data:
                        avg,p99,p100,pavg,pdev = compute_percent_and_avg(qperf_data)
                        msg = msg_format.format(vender, region, str_time, flavor, 'qperf', p99, p100, pavg, pdev, round(avg, 1))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg
                    if ping_data:
                        avg,p99,p100,pavg,pdev = compute_percent_and_avg(ping_data)
                        msg = msg_format.format(vender, region, str_time, flavor, 'ping', p99, p100, pavg, pdev, round(avg, 2))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg
                    if memcache_data:
                        avg,p99,p100,pavg,pdev = compute_percent_and_avg(memcache_data)
                        msg = msg_format.format(vender, region, str_time, flavor, 'memcache', p99, p100, pavg, pdev, int(avg))
                        with open(csv_file, 'a') as f:
                            f.write(msg+'\n')
                        print msg


def main():
    global TYPE_LIST
    generate_data_from_log()
    # print TYPE_LIST
    compute_data_by_site()
    compute_data_by_vm()
    compute_data_by_time()


if __name__ == '__main__':
    main()


print '>>>%s finish' % os.path.basename(__file__)


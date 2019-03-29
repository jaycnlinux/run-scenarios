#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = 'chengxiang'


# class Check(object):
#     def __init__(self,key, ktype):
#         self.key = key
#         self.ktype = ktype
#
#     def __set__(self, instance, value):
#         print 'call %s.__set__' % self.__class__.__name__
#         print instance.__dict__
#
#     def __get__(self, instance, owner):
#         print 'call %s.__get__' % self.__class__.__name__
#         # print instance.__dict__
#
#
# class Foo(object):
#     name = Check('name', str)
#
#     def __init__(self, name, age):
#         self.name = name
#         self.age = age
#
#
# f1 = Foo('jaycn', 18)
# f1.name = 'guoguoche'


# import re
# import os
#
#
# BASE_DIR = 'C:\\Users\\c00406647\\Desktop\\aws-qos-data\\10.00\\'
# filename = 'hw-hb-c3ne-8u-ping-3.log'
# fullpath = os.path.join(BASE_DIR, filename)
# dstfile = os.path.join(BASE_DIR, filename.replace('log', 'txt'))
#
# with open(fullpath, 'r') as f, open(dstfile, 'w') as f2:
#     count = 0
#     f2.write('ping: fetch_data\n')
#     for line in f:
#         line = line.strip()
#         # 匹配
#         ret = re.search('icmp_seq=\d+[\w\W]*time=[\w\W]*', line)
#         if ret:
#             count += 1
#             ret_str = re.split("[ =]", ret.group())
#             try:
#                 unit = ret_str[6]
#                 lat = round(float(ret_str[5]), 3)
#             except ValueError as e:
#                 lat = 0.0
#             except Exception as e:
#                 lat = 0.0
#             f2.write(str(lat)+'\n')
#             print lat


import os
import re
import time


BASE_DIR = 'C:\\Users\\administrator\\Desktop\\aws-qos-data\\'
file_dict = {'bw': 'bw.txt', 'qperf': 'qperf.txt', 'ping': 'ping.txt', 'memcached': 'memcached.txt'}


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
                bw = round(float(bw_str))
                ret.append(bw)
            if re.search(r_end, line):
                b_begin = False
    return ret


@check_name
def process_qperf(filename=''):
    pass


@check_name
def process_ping(filename=''):
    pass


@check_name
def process_memcache(filename=''):
    pass


def process_data(basedir=''):
    if not basedir:
        return
    all_file = os.listdir(basedir)
    file_list ={}
    data = {}
    # generate file dict
    for f in all_file:
        if os.path.isfile(os.path.join(basedir, f)):
            ret = f.split('-')
            ftime = ret[0]
            vender = ret[1]
            region = ret[2]
            flavor = ret[3] + '-' + ret[4]
            vm = ret[5].split('.')[0]
            ele= {}
            ele['vender'] = vender
            ele['region'] = region
            ele['time'] = ftime
            ele['file'] = os.path.join(basedir, f)
            ele['vm'] = vm
            ele['isread'] = False
            if flavor not in file_list.keys():
                file_list[flavor] = []
            file_list[flavor].append(ele)
    # generate
    for k,v in file_list.items():
        for record in v:
            print process_sar(record['file'])
            qperf_data = process_qperf(record['file'])
            ping_data = process_ping(record['file'])
            memcache_data = process_memcache(record['file'])



# for dirname in os.listdir(BASE_DIR):
#     cur_dir = os.path.join(BASE_DIR, dirname)
#     process_data(cur_dir)
cur_dir = '15.00'
process_data(os.path.join(BASE_DIR, cur_dir))
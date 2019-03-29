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
BASE_DIR = 'C:\\Users\\c00406647\\Desktop\\aws-qos-data\\'
file_dict = {'bw': 'bw.txt', 'qperf': 'qperf.txt', 'ping': 'ping.txt', 'memcached': 'memcached.txt'}


def check_name(func):
    def wrapper(*args, **kwargs):
        if len(args) == 0 and len(kwargs) == 0:
            print '文件名都没有，搞个毛啊'
        else:
            # print 'call %s, file=%s' % (func.__name__ , args)
            func(*args, **kwargs)
    return wrapper


@check_name
def process_sar(filename=''):
    # print os.path.basename(fullname)
    # print os.path.basename(os.path.dirname(fullname))
    pass


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
    file_list = []
    for f in all_file:
        if os.path.isfile(os.path.join(BASE_DIR, dirname, f)):
            file_list.append(f)
    for f in file_list:
        fullname = os.path.join(BASE_DIR, cur_dir, f)
        process_sar(fullname)
        process_qperf(fullname)
        process_ping(fullname)
        process_memcache(fullname)


for dirname in os.listdir(BASE_DIR):
    cur_dir = os.path.join(BASE_DIR, dirname)
    process_data(cur_dir)


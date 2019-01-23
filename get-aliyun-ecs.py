#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = 'chengxiang'
"""
功   能：抓阿里云ECS规格页面，并把最大规格、详细规格打出来，便于统计
使用方法：直接运行，无需参数
"""

import time
import json
import requests
from bs4 import BeautifulSoup


# 全局变量
URL = "https://help.aliyun.com/document_detail/25378.html"


# 对齐函数，返回一行对齐字符串
def align_left(record, is_header=False):
    header_length = [25, 10, 10, 5, 10, 5, 5]
    index = 0
    ret_value = ''

    for data in record:
        str_len = 0
        for i in data:
            # 中文宽度为2，ASCII宽度为1
            if len(i.encode('utf-8').decode('unicode_escape')) > 1:
                str_len += 2
            else:
                str_len += 1

        # 不够长度，需要填充空格
        padding_len = header_length[index] - str_len
        if padding_len > 0:
            data = '%s%s' % (data, ' ' * padding_len)

        index += 1
        ret_value += data

    if is_header:
        ret_value += "\n"
        for i in header_length:
            ret_value += '=' * i
    return ret_value


# 解析一个表格，每一行是一个列表元素
def parse_table(table):
    # 返回列表
    ret_value = []
    # 有效性判断
    keys = json.dumps(["实例", "CPU", "内存", "带宽", "收发包", "RoCE", "多队列"], encoding='UTF-8', ensure_ascii=False)
    keys = keys.replace("[", "").replace("]", "").replace("\"", "").replace(" ", "")
    keys = keys.split(",")
    keys_index = []

    # 获取表格头部th
    table_head_tmp = []
    for tr in table.findAll('tr'):
        for th in tr.findAll('th'):
            table_head_tmp.append(th.getText())

    # 空头部，直接返回
    if len(table_head_tmp) <= 0:
        return ret_value

    # 编码转换，以中文形式存放在list
    table_head = json.dumps(table_head_tmp, encoding='UTF-8', ensure_ascii=False)
    table_head = table_head.replace("[", "").replace("]", "").replace("\"", "").replace(" ", "")
    table_head = table_head.split(",")

    # 头部匹配，只有keys字段全部在th表头中找到，才是我们要的表格，此处要进行RoCE判断，因为有的表格没有
    match_count = 0
    index = 0
    for i in table_head:
        index += 1
        for k in keys:
            if k in i:
                keys_index.append(index-1)
                match_count += 1

    # 没有抓到全匹配的必须字段，直接返回，其中RoCE为可选，因此-1
    if match_count < len(keys) - 1:
        return ret_value

    # 命中了，开始抓取flavor内容
    for tr in table.findAll('tr'):
        index = 0
        record = []
        td = tr.findAll('td')
        for v in td:
            if index in keys_index:
                v1 = str(v.getText())
                # 去掉数字末尾的0
                if ".0" in v1:
                    v1 = v1.rstrip("0").rstrip(".")

                record.append(v1)
            index += 1

        if len(record) > 0:
            # RoCE补齐，如果一行元素个数小于7，说明没有RoCE
            if len(record) < 7:
                record.insert(5, "x")

            ret_value.append(record)

    return ret_value


# 爬阿里云ECS实例类型
def get_aliyun_ecs(target_url=URL):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
    req = ""
    ret_value = []

    while True:
        try:
            print "try to GET %s, please wait..." % URL
            req = requests.get(target_url, headers=headers)
            break
        except Exception:
            print "GET %s Failed, sleep 5s and try again" % URL
            time.sleep(5)
            pass
    soup = BeautifulSoup(req.text, "html.parser")
    tables = soup.findAll('table')

    for i in range(0, len(tables)):
        tmp_data = parse_table(tables[i])
        if len(tmp_data) > 0:
            ret_value.append(tmp_data)

    # 打印关键字
    keys = json.dumps(["实例", "CPU", "内存", "带宽", "收发包", "RoCE",  "多队列"], encoding='UTF-8', ensure_ascii=False)
    keys = keys.replace("[", "").replace("]", "").replace("\"", "").replace(" ", "")
    keys = keys.split(",")
    # 打印最大规格实例
    print "=" * 70
    tb_header = align_left(keys, is_header=True)

    if len(tb_header) > 0:
        print tb_header

    for r in ret_value:
        record = [r[-1][0], r[-1][1], r[-1][2], r[-1][3], r[-1][4], r[-1][5], r[-1][6]]
        tb_data = align_left(record, is_header=False)
        print tb_data

    # 打印详细输出
    print
    print "=" * 70
    raw_input("%sPress Enter for details%s" % (" " * 25, " " * 25))
    tb_header = align_left(keys, is_header=True)
    if len(tb_header) > 0:
        print tb_header

    for r in ret_value:
        for r1 in r:
            record = [r1[0], r1[1], r1[2], r1[3], r1[4], r1[5], r1[6]]
            tb_data = align_left(record)
            if len(tb_data) > 0:
                print tb_data
        print "-" * 70


# 主函数main
def main():
    global URL
    get_aliyun_ecs(URL)
    raw_input("Press Enter to exit")


# 全局入口
if __name__ == '__main__':
    main()

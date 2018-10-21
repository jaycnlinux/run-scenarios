#!/bin/bash
# modify date: 2018-10-21
# This is the default setting of networking multiqueue and RPS/XPS/RFS on ECS.
# 1. enable multiqueue if available
# 2. enable RPS/XPS optimization
# 3. enable RFS optimization
# 4. start irqbalance service

# set and check multiqueue
function set_check_multiqueue()
{
    eth=$1
    log_file=$2
    queue_num=$(ethtool -l $eth | grep -iA5 'pre-set' | grep -i combined | awk {'print $2'})
    if [ $queue_num -gt 1 ]; then
        # set multiqueue
        ethtool -L $eth combined $queue_num
        # check multiqueue setting
        cur_q_num=$(ethtool -l $eth | grep -iA5 current | grep -i combined | awk {'print $2'})
        if [ "X$queue_num" != "X$cur_q_num" ]; then
            echo "Failed to set $eth queue size to $queue_num" >> $log_file
            echo "after setting, pre-set queue num: $queue_num , current: $cur_q_num" >> $log_file
            return 1
        else
            echo "OK. set $eth queue size to $queue_num" >> $log_file
        fi
    else
        echo "only support $queue_num queue; no need to enable multiqueue on $eth" >> $log_file
    fi
}

# calculate the cpuset for RPS/XPS cpus
function cal_cpuset()
{
    cpu_num=$(grep -c processor /proc/cpuinfo)    #计算出cpu个数
    quotient=$((cpu_num/8))                       #取8的商
    if [ $quotient -gt 2 ]; then                  #cpu>16core
        quotient=2
    elif [ $quotient -lt 1 ]; then                #cpu<8core
        quotient=1
    fi
    for i in $(seq $quotient)
    do
        cpuset="${cpuset}f"                       #设置掩码,N个f,N=cpu个数
    done
    if [ $cpu_num -lt 4 ]; then                   #cpu<4core，之所以这么区别，是因为4,8,16,32...等的cpu可以用F FF FFFF FFFFFFFF来掩盖，而1 2 3个cpu，则不是F
        for i in $(seq $cpu_num)
        do
            bin_mask="${bin_mask}1"               #设置掩码,N个1,N=cpu个数
        done
        ((cpuset=2#${bin_mask}))                  #将1111用2进制进行运算,例如111=7  11=3
    fi
    echo $cpuset
}

# enable RPS/XPS feature
function set_rps_xps()
{
    eth=$1
    cpuset=$2
    for rps_file in $(ls /sys/class/net/${eth}/queues/rx-*/rps_cpus)
    do
        echo $cpuset > $rps_file
    done
    for xps_file in $(ls /sys/class/net/${eth}/queues/tx-*/xps_cpus)
    do
        echo $cpuset > $xps_file
    done
}

# check RPS/XPS cpus setting
function check_rps_xps()
{
    eth=$1
    exp_cpus=$2
    log_file=$3
    ((exp_cpus=16#$exp_cpus))
    ret=0
    for rps_file in $(ls /sys/class/net/${eth}/queues/rx-*/rps_cpus)
    do
        ((cur_cpus=16#$(cat $rps_file | tr -d ",")))
        if [ "X$exp_cpus" != "X$cur_cpus" ]; then
            echo "Failed to check RPS setting on $rps_file" >> $log_file
            echo "expect: $exp_cpus, current: $cur_cpus" >> $log_file
            ret=1
        else
            echo "OK. check RPS setting on $rps_file" >> $log_file
        fi
    done
    for xps_file in $(ls /sys/class/net/${eth}/queues/tx-*/xps_cpus)
    do
        ((cur_cpus=16#$(cat $xps_file | tr -d ",")))
        if [ "X$exp_cpus" != "X$cur_cpus" ]; then
            echo "Failed to check XPS setting on $xps_file" >> $log_file
            echo "expect: $exp_cpus, current: $cur_cpus" >> $log_file
            ret=1
        else
            echo "OK. check XPS setting on $xps_file" >> $log_file
        fi
    done
    return $ret
}

# enable RFS feature
function set_check_rfs()
{
    log_file=$1
    total_queues=0
    rps_flow_cnt_num=4096
    rps_flow_entries_file="/proc/sys/net/core/rps_sock_flow_entries"
    ret=0
    for j in $(ls -d /sys/class/net/eth*)
    do
        eth=$(basename $j)
        queues=$(ls -ld /sys/class/net/$eth/queues/rx-* | wc -l)
        total_queues=$(($total_queues + $queues))
        for k in $(ls /sys/class/net/$eth/queues/rx-*/rps_flow_cnt)
        do
            echo $rps_flow_cnt_num > $k
            if [ "X$rps_flow_cnt_num" != "X$(cat $k)" ]; then
                echo "Failed to set $rps_flow_cnt_num to $k" >> $log_file
                ret=1
            else
                echo "OK. set $rps_flow_cnt_num to $k" >> $log_file
            fi
        done
    done
    total_flow_entries=$(($rps_flow_cnt_num * $total_queues))
    echo $total_flow_entries > $rps_flow_entries_file
    if [ "X$total_flow_entries" != "X$(cat $rps_flow_entries_file)" ]; then
        echo "Failed to set $total_flow_entries to $rps_flow_entries_file" >> $log_file
        ret=1
    else
        echo "OK. set $total_flow_entries to $rps_flow_entries_file" >> $log_file
    fi
    return $ret
}

# start irqbalance service
function start_irqblance()
{
    log_file=$1
    ret=0
    cpu_num=$(grep -c processor /proc/cpuinfo)
    if [ $cpu_num -lt 2 ]; then
        echo "No need to start irqbalance" >> $log_file
        echo "found $cpu_num processor in /proc/cpuinfo" >> $log_file
        return $ret
    fi
    if [ "X" = "X$(ps -ef | grep irqbalance | grep -v grep)" ]; then
        systemctl start irqbalance
        sleep 1
        systemctl status irqbalance &> /dev/null
        if [ $? -ne 0 ]; then
            service irqbalance start
            if [ $? -ne 0 ]; then
                echo "Failed to start irqbalance" >> $log_file
                ret=1
            fi
        else
            echo "OK. irqbalance started." >> $log_file
        fi
    else
        echo "irqbalance is running, no need to start it." >> $log_file
    fi
    return $ret
}

# main logic
function main()
{
    ecs_network_log=/var/log/ecs_network_optimization.log
    ret_value=0
    rps_xps_cpus=$(cal_cpuset)       #等到cpu掩码，例如f   ff ffff     11  111  1
    echo "running $0" > $ecs_network_log
    # we assume your NIC interface(s) is/are like eth*
    eth_dirs=$(ls -d /sys/class/net/eth*)
    if [ $? -ne 0 ];then
        echo "Failed to find eth*  , sleep 30" >> $ecs_network_log
        sleep 30
        eth_dirs=$(ls -d /sys/class/net/eth*)
    fi
    echo "find eth device is : $eth_dirs" >> $ecs_network_log
    echo "========  ECS network setting starts $(date +'%Y-%m-%d %H:%M:%S') ========" >> $ecs_network_log

    for i in $eth_dirs
    do
        cur_eth=$(basename $i)
        echo "set and check multiqueue on $cur_eth" >> $ecs_network_log
        set_check_multiqueue $cur_eth $ecs_network_log
        if [ $? -ne 0 ]; then
            echo "Failed to set multiqueue on $cur_eth" >> $ecs_network_log
            ret_value=1
        fi
        echo "enable RPS/XPS on $cur_eth" >> $ecs_network_log
        set_rps_xps $cur_eth $rps_xps_cpus
        echo "check RPS/XPS on $cur_eth" >> $ecs_network_log
        check_rps_xps $cur_eth $rps_xps_cpus $ecs_network_log
        if [ $? -ne 0 ]; then
            echo "Failed to enable RPS/XPS on $cur_eth" >> $ecs_network_log
            ret_value=1
        fi
    done
    echo "set and check RFS" >> $ecs_network_log
    set_check_rfs $ecs_network_log
    if [ $? -ne 0 ]; then
        ret_value=1
    fi
    echo "start irqbalance service" >> $ecs_network_log
    start_irqblance $ecs_network_log
    if [ $? -ne 0 ]; then
        ret_value=1
    fi
    echo "========  ECS network setting END $(date +'%Y-%m-%d %H:%M:%S')  ========" >> $ecs_network_log
    return $ret_value
}

# program starts here
main
exit $?

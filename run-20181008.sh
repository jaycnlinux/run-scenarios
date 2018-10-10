#!/bin/bash


#########################参数说明#########################
#DIR:日志存放目录，默认在当前程序下创建logm目录
#SUBDIR：每一次测试生成的子文件夹格式，示例20180703-092800
#ECS_ETH0：被测ECS的主网卡eth0 IP地址，用于测试单网卡情况，自动从list1.txt里读取第1行IP
#PEER_ETH0：1V1时对端ECS的主网卡eth0 IP地址，用于测试单网卡情况，自动从list2.txt里读取第1行IP
#PEER_ETH1：1V1时对端ECS的第2块网卡，用于测试多网卡场景，如多卡带宽、pps抢占，多卡整ECS连接数控制，当前需要配合手工修改portbw_netperf()，portbw_netperf()函数，计划以后只需要修改本处，函数内自动适配
#PEER_ETH2：1V1时对端ECS的第3块网卡，用于测试多网卡场景，如多卡带宽、pps抢占，多卡整ECS连接数控制，当前需要配合手工修改portbw_netperf()，portbw_netperf()函数，计划以后只需要修改本处，函数内自动适配
#PEER_ETH3：1V1时对端ECS的第4块网卡，用于测试多网卡场景，如多卡带宽、pps抢占，多卡整ECS连接数控制，当前需要配合手工修改portbw_netperf()，portbw_netperf()函数，计划以后只需要修改本处，函数内自动适配
#PAIR_PORT1：极限测试打流最小端口号
#PAIR_PORT2：极限测试打流最大端口号
#FLAVOR_PORTORT1：测试flavor模型时打流最小端口号
#FLAVOR_PORTORT2：测试flavor模型时打流最大端口号
#PAIR_NUM: 服务器pair对数
#PEILIAN_NUM：陪练机个数
#PPS_BW：iperf3测试pps时指定的-b带宽

DIR="log"
SUBDIR=`date +"%Y%m%d-%H%M%S"`
LOGFILE="./log/real-${SUBDIR}.log"
FILE_LIST1="list1.txt"
FILE_LIST2="list2.txt"
ECS_ETH0="AUTO GET"
PEER_ETH0="AUTO GET"
PEER_ETH1="192.168.1.221"
PEER_ETH2="192.168.2.140"
PEER_ETH3="192.168.3.140"
PAIR_PORT1=7001
PAIR_PORT2=7016
FLAVOR_PORT1=7001
FLAVOR_PORT2=7032
PAIR_NUM=0
PEILIAN_NUM=0
PPS_BW="100M"

# 定义5个数组：IP地址列表1、2;命令列表;15V15 sar文件列表;1打多陪练IP列表
declare -a IP_LIST1
declare -a IP_LIST2
declare -a CMD
declare -a F
declare -a PEILIAN_IP

# 结果存放及测试项标记
b=0

##############################################
# 判断文件列表是否存在
if [ ! -f $FILE_LIST1 ];then
    echo "file $FILE_LIST1 not exist!!!,exit"
    exit -1
fi

if [ ! -f $FILE_LIST2 ];then
    echo "file $FILE_LIST2 not exist!!!,exit"
    exit -1
fi

# 初始化参数
if [ -f $FILE_LIST1 ];then
    PAIR_NUM=`cat $FILE_LIST1 | wc -l`
else
    PAIR_NUM=0
fi

if [ -f $FILE_LIST2 ];then
    PEILIAN_NUM=`cat $FILE_LIST2 | wc -l`
else
    PEILIAN_NUM=0
fi

ECS_ETH0=`head -n 1 $FILE_LIST1`
PEER_ETH0=`head -n 1 $FILE_LIST2`

# flavor PPS测试默认iperf3发包大小100M
if [ ! $1 ];then
    PPS_BW="100M"
else
    PPS_BW="${1}M"
fi
##############################################


# 颜色提示
function warn()
{
    msg="warning"

    if [ ! -z "$1" ];then
    msg=$1
    fi

    echo -e "\033[33m${msg}\033[0m" >> $LOGFILE
}


function ok()
{
    msg="ok"

    if [ ! -z "$1" ];then
        msg=$1
    fi

    echo -e "\033[32m${msg}\033[0m" >> $LOGFILE
}


function error()
{
    msg="error"

    if [ ! -z "$1" ];then
        msg=$1
    fi

    echo -e "\033[31m${msg}\033[0m" >> $LOGFILE
}


# 创建新日志
function create_new_real_log()
{
    SUBDIR=`date +"%Y%m%d-%H%M%S"`
    LOGFILE="./${DIR}/real-${SUBDIR}.log"

    if [ ! -d ./${DIR} ];then
        mkdir -p ./${DIR}
    fi

    touch $LOGFILE
}


# 判断给定IP地址的版本，是IPV4还是IPV6
function get_ip_version()
{
    #默认返回v4
    ret=4

    if [ $1 ];then
        ip_addr=`echo "$1" | grep \: | wc -l`
        if [ $ip_addr -ge 1 ];then
            ret=6
        fi
    fi

    echo $ret
    return $ret
}


# 是否存活，用ping探测,0=不通 1=通,IPV4/IPV6通用
function isalive()
{
    if [ ! $1 ];then
        echo 0
        return 0
    fi

    host=$1
    #判断received数，0表示不通，大于0就通了
    ip_ver=`get_ip_version $host`
    echo "IP_VERSION=$ip_ver"
    if [ $ip_ver -eq 6 ];then
        icmpret=`ping -6 $host -c 2 -W 1 | grep received | awk '{print $4}'`
    else
        icmpret=`ping $host -c 2 -W 1 | grep received | awk '{print $4}'`
    fi

    if [ $icmpret -eq 0 ];then
        echo 0
        return 0
    else
        echo 1
        return 1
    fi

    echo 0
    return 0
}


# 获取IP pair对列表，15v15用，填入数组L1,L2,IPV4/IPV6通用
function get_ip_pair_list()
{
    echo -e "\nread ip pair list...\c"
    for i in `seq 1 $PAIR_NUM`;do
        IP_LIST1[$i]=`cat $FILE_LIST1 | sed -n "${i}p"`
        IP_LIST2[$i]=`cat $FILE_LIST2 | sed -n "${i}p"`
    done

    echo -e "pair_num=$PAIR_NUM \c"
    ok "done"
}


# 陪练机ip，1V8用，IPV4/IPV6通用
function read_flavor_peilian_ip()
{
    echo -e "\nread peilian client ip...\c"
    PEILIAN_NUM=`cat $FILE_LIST2 | wc -l`
    for i in `seq 1 $PEILIAN_NUM`;do
        PEILIAN_IP[$i]=`cat $FILE_LIST2 | sed -n "${i}p"`
    done

    echo "num=$PEILIAN_NUM done"
}


# 拷贝iperf3.3,IPV4/IPV6通用
function copy_iperf3_3()
{
    get_ip_pair_list
    read_flavor_peilian_ip

    # 15V15主机
    tmpcount=1
    for i in `seq 1 $PAIR_NUM`;do
        for host in ${IP_LIST1[$i]} ${IP_LIST2[$i]};do
            echo -e "No.$tmpcount\tcopy iperf3.3 to $host\t\t\c" >> $LOGFILE
            ret=`get_ip_version $host`
            if [ $ret -eq 6 ];then
                scp /usr/local/bin/iperf3 [$host]:/usr/bin/iperf3 2>&1 > /dev/null
                scp /usr/local/lib/libiperf.so.0 [$host]:/usr/local/lib/libiperf.so.0 2>&1 > /dev/null
            else
                scp /usr/local/bin/iperf3 $host:/usr/bin/iperf3 2>&1 > /dev/null
                scp /usr/local/lib/libiperf.so.0 $host:/usr/local/lib/libiperf.so.0 2>&1 > /dev/null
            fi
        done
        ok "done"

        ((tmpcount++))
    done
    
    # 1v8主机
    tmpcount=1
    for i in `seq 1 $PEILIAN_NUM`;do
        host=${PEILIAN_IP[$i]}
        echo -e "No.$tmpcount\tcopy iperf3.3 to $host\t\t\c" >> $LOGFILE
        ret=`get_ip_version $host`
        if [ $ret -eq 6 ];then
            scp /usr/local/bin/iperf3 [$host]:/usr/bin/iperf3 2>&1 > /dev/null
            scp /usr/local/lib/libiperf.so.0 [$host]:/usr/local/lib/libiperf.so.0 2>&1 > /dev/null
        else
            scp /usr/local/bin/iperf3 $host:/usr/bin/iperf3 2>&1 > /dev/null
            scp /usr/local/lib/libiperf.so.0 $host:/usr/local/lib/libiperf.so.0 2>&1 > /dev/null
        fi
        ok "done"

        ((tmpcount++))
    done

    sleep 1
}


# 启动C1000k，shell没适配好，用python做了
function start_C1000k_server()
{
   for j in `seq 1 $PAIR_NUM`;do
     h1=${L1[$j]}
     h2=${L2[$j]}

     echo -e "start C1000k_server at $h1...\c" >> $LOGFILE
     ssh $h1 "/root/C1000k-master/server 9000" 2>&1 > /dev/null &
     sleep 0.01
     ok "done"

     echo -e "start C1000k_server at $h2...\c" >> $LOGFILE
     ssh $h2 "/root/C1000k-master/server 9000" 2>&1 > /dev/null &
     sleep 0.01
     ok "done"
   done

   sleep 1
}


# netperf发送模板，IPV4/IPV6通用
# 参数：$1发送IP, $2接收IP, $3起始port, $4终止port, $5类型, $6测试时长, $7 包长
function start_run_send_netperf_template()
{
    client=$1
    server=$2
    port1=$3
    port2=$4
    test_type=$5
    test_time=$6
    pkt_len=$7

    tmpcount=1
    echo -e "\thost=$client --> $server flow:\c" >> $LOGFILE
    for i in `seq $port1 $port2`;do
        cmd="netperf -H $server -p $i -t $test_type -l test_time -- -m pkt_len"
        ssh -t -t $client $cmd 2>&1 > /dev/null &
        echo -e "$tmpcount \c" >> $LOGFILE
        ((tmpcount++))
        sleep 0.1
    done

    ok "start_run_netperf done,port1=$port1 port2=$port2 type=$test_type time=$test_time pkt_len=$pkt_len"
}


# 单机测试：双向带宽，IPV4/IPV6通用
function start_run_dual_netperf()
{
    tmpcount=1
    echo -e "\nhost: ${ECS_ETH0} --> ${PEER_ETH0}\tflow:\c" >> $LOGFILE
    for i in `seq $PAIR_PORT1 $PAIR_PORT2`;do
        cmd="netperf -H $PEER_ETH0 -p $i -t TCP_STREAM -l 86400 -- -m 1440"
        ssh -t -t $ECS_ETH0 $cmd 2>&1 > /dev/null &

        echo -e "${tmpcount} \c" >> $LOGFILE
        ((tmpcount++))
        sleep 0.1
    done


    tmpcount=1
    echo -e "\nhost: ${PEER_ETH0} --> ${ECS_ETH0}\tflow:\c"
    for i in `seq $PAIR_PORT1 $PAIR_PORT2`;do
        cmd="netperf -H $ECS_ETH0 -p $i -t TCP_STREAM -l 86400 -- -m 1440"
        ssh -t -t $PEER_ETH0 $cmd 2>&1 > /dev/null &

        echo -e "$tmpcount \c" >> $LOGFILE
        ((tmpcount++))
        sleep 0.1
    done

    sleep 1
    echo -e "\nstart_run_dual_netperf done"
}


# 单机测试：多网卡带宽/PPS抢占,IPV4/IPV6通用
# 自动适配流数
# 参数：$1测试类型TCP_STREAM/UDP_STREAM, $2 包长1440/64
function start_run_multi_port_send_netperf_template()
{
    test_type=$1
    pkt_len=$2

    port_num=`ifconfig | grep ^eth | wc -l`
    if [ $portnum -le 0 ];then
        echo "can not found any eth,exit!!!"
        return
    fi

    echo "start eth0"
    tmpflow=`expr $PAIR_PORT2 - $PAIR_PORT1 + 1 - $portnum + 1 `

    # eth0
    echo -e "\nhost:$ECS_ETH0 --> $PEER_ETH0 eth0 flow:\c" >> $LOGFILE
    for i in `seq 1 $tmpflow`;do
        tmpport=`expr PAIR_PORT1 + $i - 1`
        cmd="netperf -H $PEER_ETH0 -p $tmpport -t $test_type -l 86400 -- -m $pkt_len"
        ssh -t -t $ECS_ETH0 $cmd 2>&1 > /dev/null &
        sleep 0.1
    done

    # ethxxx
    for i in `seq 2 $portnum`; do
        sleep 5
        tmpeth=`expr $i - 1`
        if [[ $tmpeth -eq 1 ]]; then
            host=$PEER_ETH1
        elif [[ $tmpeth -eq 2 ]]; then
            host=$PEER_ETH2
        elif [[ $tmpeth -eq 3 ]]; then
            host=$PEER_ETH3
        fi

        echo -e "\nhost:$ECS_ETH0 --> $host eth$tmpeth flow:\c" >> $LOGFILE
        tmpport=`expr $PAIR_PORT1 + $tmpflow -1 + $i - 1`
        cmd="netperf -H $host -p $tmpport -t $test_type -l 86400 -- -m $pkt_len"
        ssh -t -t $C1 $cmd 2>&1 > /dev/null &  
        sleep 0.1
    done

    echo -e "\nstart_run_multi_port_send_netperf_template done,type=$test_type,pkt_len=$pkt_len"
}


# 延迟测试：延迟和丢包,IPV4/IPV6通用
function get_ping_and_loss()
{
    sleep 5
    echo -e "\n\n$ECS_ETH0 ping start"
    ret=`get_ip_version $ECS_ETH0`
    if [ $ret -eq 6 ];then
        ping -6 -c 60 $ECS_ETH0 | grep -E "avg|loss"
    else
        ping -c 60 $ECS_ETH0 | grep -E "avg|loss"
    fi

    sleep 5
    echo -e "\n\n$ECS_ETH0 loss start"
    ret=`get_ip_version $ECS_ETH0`
    if [ $ret -eq 6 ];then
        ping -6 -c 10000 -i 0.01 $ECS_ETH0 | grep -E "avg|loss"
    else
        ping -6 -c 10000 -i 0.01 $ECS_ETH0 | grep -E "avg|loss"
    fi
}


# 单机测试1v1：启动一个netserver,IPV4/IPV6语法通用
function start_one_to_one_netserver()
{ 
    echo -e "start netserver...\c"
    for i in `seq $PAIR_PORT1 $PAIR_PORT2`;do
        ssh $ECS_ETH0 "netserver -p $i 2>&1 > /dev/null" 2>&1 > /dev/null
        sleep 0.01
        ssh $PEER_ETH0 "netserver -p $i 2>&1 > /dev/null" 2>&1 > /dev/null
        sleep 0.01
    done

    ok "done"
    sleep 1
}


# 多机抢占15v15：启动IP地址列表里所有netserver,IPV4/IPV6通用
function start_all_netserver()
{
    for i in `seq 1 $PAIR_NUM`;do
        h1=${IP_LIST1[$i]}
        h2=${IP_LIST2[$i]}

        echo -e "start netserver at $h1...\c" >> $LOGFILE
        for j in `seq $PAIR_PORT1 $PAIR_PORT2`;do
            ssh $h1 "netserver -p $j" 2>&1 > /dev/null
            sleep 0.1
        done
        ok "done"


        echo -e "start netserver at $h2...\c" >> $LOGFILE
        for j in `seq $PAIR_PORT1 $PAIR_PORT2`;do
            ssh $h2 "netserver -p $j" 2>&1 > /dev/null
            sleep 0.1
        done
        ok "done"
    done

    sleep 1
}


#多机抢占15v15：同时发送,IPV4/IPV6通用
function start_all_send_bw_netperf()
{
    for i in `seq 1 $PAIR_NUM`;do
        tmpclient=""
        tmpserver=""
     
        tmpclient=${IP_LIST1[$i]}
        tmpserver=${IP_LIST2[$i]}
     
        echo -e "No.$i\c" >> $LOGFILE
        start_run_send_netperf_template $tmpclient $tmpserver $PAIR_PORT1 $PAIR_PORT2 "TCP_STREAM" 86400 1440
    done
    sleep 1
}


#多机抢占15v15：同时接收，IPV4/IPV6通用
function start_all_recv_bw_netperf()
{
    for i in `seq 1 $PAIR_NUM`;do
        tmpclient=""
        tmpserver=""
     
        tmpclient=${IP_LIST1[$i]}
        tmpserver=${IP_LIST2[$i]}
     
        echo -e "No.$i\c" >> $LOGFILE
        start_run_send_netperf_template $tmpserver $tmpclient $PAIR_PORT1 $PAIR_PORT2 "TCP_STREAM" 86400 1440
    done
    sleep 1
}


#多机抢占15v15：同时发送netperf UDP 64,IPV4/IPV6通用
function start_all_send_pps_netperf()
{
    for i in `seq 1 $PAIR_NUM`;do
        tmpclient=""
        tmpserver=""

        tmpclient=${IP_LIST1[$i]}
        tmpserver=${IP_LIST2[$i]}

        echo -e "No.$i\c" >> $LOGFILE
        start_run_send_netperf_template $tmpclient $tmpserver $PAIR_PORT1 $PAIR_PORT2 "UDP_STREAM" 86400 64
    done
    sleep 1
}

# !!!!!!上次看到这里
#多机抢占15v15：同时接收netperf UDP 64,IPV4/IPV6通用
function start_all_recv_pps_netperf()
{
    for i in `seq 1 $PAIR_NUM`;do
        tmpclient=""
        tmpserver=""

        tmpclient=${L1[$i]}
        tmpserver=${L2[$i]}

        echo -e "No.$i\c" >> $LOGFILE
        start_run_send_netperf_template $tmpserver $tmpclient $PAIR_PORT1 $PAIR_PORT2 "UDP_STREAM" 86400 64
    done
    sleep 1
}


# 单机测试：多网卡流量统计,IPV4/IPV6通用
function get_one_sar()
{
    rm -f eth.txt
    sleep 20
    echo -e "\n\nsar begin,host=$ECS_ETH0" 
    ssh $ECS_ETH0 "sar -n DEV 1 60" >> eth.txt &
    sleep 65

    cat eth.txt | grep eth | grep -i ave
}


#多机抢占15v15：获取60s sar,IPV4/IPV6通用
function get_all_sar()
{
    sleep 5
    echo -e "\nget all sar...\c"
    for i in `seq 1 $PAIR_NUM`;do
        tmpclient=${L1[$i]}
        
        ssh -t -t $tmpclient "sar -n DEV 1 60"  > ./${DIR}/${SUBDIR}/${tmpclient}.txt &
        sleep 0.1
    done
    
    sleep 65
    ok "done"
}


#多机数据搜集15v15发送带宽，打印结果，IPV4/IPV6通用
function show_all_send_bw()
{
    tmp=0
    
    for i in `ls ./${DIR}/${SUBDIR}/*.txt`;do
        ((tmp++)) 
        F[$tmp]=$i
    done

    for j in `seq 1 60`;do
        for i in `seq 1 $tmp`;do
            bw=`cat ${F[$i]} | grep eth0 | sed -n "${j}p" | awk '{print $7}'`
            echo -e "${bw},\c" >> "./${DIR}/${SUBDIR}.csv"
        done
        echo "" >> "./${DIR}/${SUBDIR}.csv"
    done
    
    echo -e "\n\nshow_all_send_bw---------------------" 
    cat "./${DIR}/${SUBDIR}.csv"
}


#多机数据搜集15v15接收带宽,打印结果，IPV4/IPV6通用
function show_all_recv_bw()
{
    tmp=0
    
    for i in `ls ./${DIR}/${SUBDIR}/*.txt`;do
        ((tmp++)) 
        F[$tmp]=$i
    done

    for j in `seq 1 60`;do
        for i in `seq 1 $tmp`;do
            bw=`cat ${F[$i]} | grep eth0 | sed -n "${j}p" | awk '{print $6}'`
            echo -e "${bw},\c" >> "./${DIR}/${SUBDIR}.csv"
        done
        echo "" >> "./${DIR}/${SUBDIR}.csv"
    done
    
    echo -e "\n\nshow_all_recv_bw---------------------" 
    cat "./${DIR}/${SUBDIR}.csv"
}


#多机发送PPS数据搜集15v15发送PPS，打印结果，IPV4/IPV6通用
function show_all_send_pps_udp64()
{
    tmp=0

    for i in `ls ./${DIR}/${SUBDIR}/*.txt`;do
        ((tmp++))
        F[$tmp]=$i
    done

    for j in `seq 1 60`;do
        for i in `seq 1 $tmp`;do
            bw=`cat ${F[$i]} | grep eth0 | sed -n "${j}p" | awk '{print $5}'`
            echo -e "${bw},\c" >> "./${DIR}/${SUBDIR}.csv"
        done
        echo "" >> "./${DIR}/${SUBDIR}.csv"
    done

    echo -e "\n\nshow_all_send_pps_udp64---------------------" 
    cat "./${DIR}/${SUBDIR}.csv"
}


#多机接收PPS数据搜集15v15接收PPS，打印结果，IPV4/IPV6通用
function show_all_recv_pps_udp64()
{
    tmp=0

    for i in `ls ./${DIR}/${SUBDIR}/*.txt`;do
        ((tmp++))
        F[$tmp]=$i
    done

    for j in `seq 1 60`;do
        for i in `seq 1 $tmp`;do
            bw=`cat ${F[$i]} | grep eth0 | sed -n "${j}p" | awk '{print $4}'`
            echo -e "${bw},\c" >> "./${DIR}/${SUBDIR}.csv"
        done
        echo "" >> "./${DIR}/${SUBDIR}.csv"
    done

    echo -e "\n\nshow_all_recv_pps_udp64---------------------" 
    cat "./${DIR}/${SUBDIR}.csv"
}


#启动C1000k client
#!!!!c1000k测试有问题，转python
function start_C1000k_client()
{
   for j in `seq 1 $PAIR_NUM`;do
     h1=${L1[$j]}
     h2=${L2[$j]}

     echo -e "start C1000k_client at $h1 to server $h2 ...\c"
     ssh $h1 "/root/C1000k-master/client $h2 9000" > /dev/null &
     sleep 0.1
     ok "done"
   done

   sleep 5

}


#启动iperf3 server,IPV4/IPV6通用
#!!!!此处待优化端口
function start_flavor_iperf3_server()
{
    tmpcount=1

    echo -e "start iperf3 server at SERVER($C1)...\c" >> $LOGFILE
    for i in `seq $FLAVOR_PORT1 $FLAVOR_PORT2`;do
        cmd="iperf3 -s -p $i 2>&1 > /dev/null &"
        ssh $C1 $cmd &
        echo -e "$tmpcount \c" >> $LOGFILE
        sleep 0.1
        ((tmpcount++))
    done
    ok "done"

    for j in `seq 1 $PEILIAN_NUM`;do
        tmpcount=1
        client=${PEILIAN_IP[$j]}
        echo -e "start iperf3 server at peilian($client)...\c" >> $LOGFILE

        for i in `seq $FLAVOR_PORT1 $FLAVOR_PORT2`;do
            cmd="iperf3 -s -p $i 2>&1 > /dev/null &"
            ssh $client $cmd &
            echo -e "$tmpcount \c" >> $LOGFILE
            sleep 0.1
            ((tmpcount++))
        done
        ok "done"
    done
    
    sleep 5
}


#启动PPS测试的netserver,IPV4/IPV6通用
#!!!!此处待优化端口
function start_FLAVOR_PORTps_netserver()
{
    tmpcount=1

    echo -e "start netserver at SERVER($C1)...\c" >> $LOGFILE
    for i in `seq $FLAVOR_PORT1 $FLAVOR_PORT2`;do
        cmd="netserver -p $i 2>&1 > /dev/null"
        ssh $C1 $cmd &
        echo -e "$tmpcount \c" >> $LOGFILE
        sleep 0.1
        ((tmpcount++))
    done
    ok "done"


    for j in `seq 1 $PEILIAN_NUM`;do
        tmpcount=1
        client=${PEILIAN_IP[$j]}
        echo -e "start netserver at peilian($client)...\c" >> $LOGFILE

        for i in `seq $FLAVOR_PORT1 $FLAVOR_PORT2`;do
            cmd="netserver -p $i 2>&1 > /dev/null"
            ssh $client $cmd &
            echo -e "$tmpcount \c" >> $LOGFILE
            sleep 0.1
            ((tmpcount++))
        done
        ok "done"
    done

    sleep 5
}


#单向最大发送带宽 TCP 1440,IPV4/IPV6通用
function flavor_send_bw_netperf()
{
    portnum=`expr $FLAVOR_PORT2 - $FLAVOR_PORT1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`

    #server发包
    j=1
    curport=$FLAVOR_PORT1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        echo -e "netperf to peilian($client)...\c" >> $LOGFILE

        for k in `seq 1 $flownum`;do
            cmd="netperf -H $client -p $curport -t TCP_STREAM -l 86400 -- -m 1440 2>&1 > /dev/null &"
            ssh $C1 $cmd &
            sleep 0.2

            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
    done
    sleep 10
}


#单向最大接收带宽 TCP 1440,IPV4/IPV6通用
function flavor_recv_bw_netperf()
{
    portnum=`expr $FLAVOR_PORT2 - $FLAVOR_PORT1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`

    #server发包
    j=1
    curport=$FLAVOR_PORT1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        echo -e "netperf from peilian($client)...\c" >> $LOGFILE

        for k in `seq 1 $flownum`;do
            cmd="netperf -H $C1 -p $curport -t TCP_STREAM -l 86400 -- -m 1440 2>&1 > /dev/null &"
            #echo $cmd
            ssh $client $cmd &
            sleep 0.2

            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
    done
    sleep 10
}


#单向最大发送带宽TCP 64,IPV4/IPV6通用
function flavor_send_bw_netperf_tcp64()
{
    portnum=`expr $FLAVOR_PORT2 - $FLAVOR_PORT1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`

    #server发包
    j=1
    curport=$FLAVOR_PORT1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        echo -e "netperf to peilian($client) TCP64...\c" >> $LOGFILE

        for k in `seq 1 $flownum`;do
            cmd="netperf -H $client -p $curport -t TCP_STREAM -l 86400 -- -m 64 2>&1 > /dev/null &"
            ssh $C1 $cmd &
            sleep 0.2

            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
    done
    sleep 10
}


#单向最大发送PPS netperf udp64,IPV4/IPV6通用
function flavor_send_bw_netperf_udp64()
{
    portnum=`expr $FLAVOR_PORT2 - $FLAVOR_PORT1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`

    #server发包
    j=1
    curport=$FLAVOR_PORT1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        echo -e "netperf to peilian($client)...\c" >> $LOGFILE

        for k in `seq 1 $flownum`;do
            cmd="netperf -H $client -p $curport -t UDP_STREAM -l 86400 -- -m 64 2>&1 > /dev/null &"
            ssh $C1 $cmd &
            sleep 0.2

            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
    done
    sleep 10
}


#单向最大接收PPS netperf udp64,IPV4/IPV6通用
function flavor_recv_pps_netperf_udp64()
{
    portnum=`expr $FLAVOR_PORT2 - $FLAVOR_PORT1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`

    #server发包
    j=1
    curport=$FLAVOR_PORT1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        echo -e "netperf from peilian($client)...\c" >> $LOGFILE

        for k in `seq 1 $flownum`;do
            cmd="netperf -H $C1 -p $curport -t UDP_STREAM -l 86400 -- -m 64 2>&1 > /dev/null &"
            #echo $cmd
            ssh $client $cmd &
            sleep 0.2

            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
    done
    sleep 10
}


#flavor单向最大发送pps，IPV4/IPV6通用
function flavor_send_pps_iperf3()
{
    portnum=`expr $FLAVOR_PORT2 - $FLAVOR_PORT1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`
    tmpcount=0

    #server发包
    j=1
    curport=$FLAVOR_PORT1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        ((tmpcount++))
        echo -e "No.${tmpcount}:pps send to peilian($client) bw=${PPS_BW} iperf3...\c" >> $LOGFILE
       
        for k in `seq 1 $flownum`;do
            cmd="iperf3 -c $client -u -p $curport -b $PPS_BW -l 64 -t 86400 --pacing-timer 10000 2>&1 > /dev/null &"
            ssh $C1 $cmd &
            sleep 0.2

            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
      done
    sleep 10
}


#flavor单向接收pps，IPV4/IPV6通用
function flavor_recv_pps_iperf3()
{
    portnum=`expr $P2 - $P1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`
    tmpcount=0

    #server发包
    j=1
    curport=$P1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        ((tmpcount++))
        echo -e "No.${tmpcount}:pps recv from peilian($client) bw=${PPS_BW} iperf3...\c" >> $LOGFILE

        for k in `seq 1 $flownum`;do
            cmd="iperf3 -c $C1 -u -p $curport -b $PPS_BW -l 64 -t 86400 --pacing-timer 10000 2>&1 > /dev/null &"
            ssh $client $cmd &
            sleep 0.2

            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
    done
    sleep 10
}


#flavor双向pps，IPV4/IPV6通用
function flavor_dual_pps_iperf3()
{
    portnum=`expr $P2 - $P1 + 1`
    flownum=`expr $portnum / $PEILIAN_NUM`
    tmpcount=0

    #server发包
    j=1
    curport=$P1

    for i in `seq 1 $PEILIAN_NUM`;do
        client=${PEILIAN_IP[$j]}
        ((tmpcount++))

        echo -e "No.${tmpcount}:pps bidirection at peilian($client) bw=${PPS_BW} iperf3...\c" >> $LOGFILE

        for k in `seq 1 $flownum`;do
            cmd="iperf3 -c $client -u -p $curport -b $PPS_BW -l 64 -t 86400 --pacing-timer 10000 2>&1 > /dev/null &"
            ssh $C1 $cmd &
            sleep 0.2
            
            cmd="iperf3 -c $C1 -u -p $curport -b $PPS_BW -l 64 -t 86400 --pacing-timer 10000 2>&1 > /dev/null &"
            ssh $client $cmd &
            sleep 0.2
            
            echo -e "${k} \c" >> $LOGFILE
            ((curport++))
        done

        ((j++))
        ok "done"
    done
    sleep 10
}


############################################################################
#停止所有netserver、netperf，IPV4/IPV6通用
function off()
{
    #关闭流顺序：从LIST1到LIST2
    kill_order="L2R"
    kill_f1=$FILE_LIST1
    kill_f2=$FILE_LIST2

    if [ $1 ];then
        if [ $1 -eq "R2L" ];then
            kill_order="R2L"
        fi
    fi

    #use pkill
    echo "try to pkill local" >> $LOGFILE
    pkill iperf3
    pkill iperf
    pkill netperf
    pkill netserver

    if [ "$kill_order" -eq "L2R"];then
        kill_f1=$FILE_LIST1
        kill_f2=$FILE_LIST2
    else
        kill_f1=$FILE_LIST2
        kill_f2=$FILE_LIST1
    fi

    echo "try to pkill remote" >> $LOGFILE
    if [ -f $kill_f1 ];then
        for i in `cat $kill_f1`;do
            echo -e "kill host ${i}...\c" >> $LOGFILE
            icmpret=`isalive $i`
            if [ $icmpret -eq 1 ];then
                ssh $i pkill iperf3
                ssh $i pkill iperf
                ssh $i pkill netperf
                ssh $i pkill netserver
                ok "done"
            else
                error "timeout"
            fi
        done
    fi

    if [ -f $kill_f2 ];then
        for i in `cat $kill_f2`;do
            echo -e "kill host ${i}...\c" >> $LOGFILE
            icmpret=`isalive $i`
            if [ $icmpret -eq 1 ];then
                ssh $i pkill iperf3
                ssh $i pkill iperf
                ssh $i pkill netperf
                ssh $i pkill netserver
                ok "done"
            else
                error "timeout"
            fi
        done
    fi

    ok "off done"
}


#功能入口：单机单网口测试netperf
function one_to_one_bw_netperf()
{
    off
    start_netserver
    maxbw_netperf
    sar
    pingloss
}


#功能入口：单机单网口双向测试netperf
function one_to_one_dual_bw_netperf()
{
    off
    start_netserver
    dualbw_netperf
    sar
}


#功能入口：单机多端口发送带宽测试netperf
function one_to_one_multi_port_send_bw_netperf()
{
    off
    start_netserver
    portbw_netperf
    sar
}


#功能入口：单机多端口测试netperf
function one_to_one_multi_port_send_pps_netperf()
{
    off
    start_netserver
    portpps_netperf
    sar
}


#功能入口：多机发送带宽netperf TCP 1440
function all_ecs_send_bw_netperf_tcp1440()
{
    if [ ! -d ./${DIR}/${SUBDIR} ];then
        mkdir -p ./${DIR}/${SUBDIR}
    fi

    off
    get_ip_pair_list   
    start_all_server
    start_all_send_bw_netperf_tcp1440
    get_all_sar
    show_all_send_bw
}


#功能入口：多机接收带宽netperf TCP 1440
function all_ecs_recv_bw_netperf_tcp1440()
{
    if [ ! -d ./${DIR}/${SUBDIR} ];then
        mkdir -p ./${DIR}/${SUBDIR}
    fi

    off
    get_ip_pair_list
    start_all_server
    start_all_recv_bw_netperf_tcp1440
    get_all_sar
    show_all_recv_bw
}


#功能入口：多机发送测试netperf udp 64
function all_ecs_send_pps_netperf_udp64()
{
    if [ ! -d ./${DIR}/${SUBDIR} ];then
        mkdir -p ./${DIR}/${SUBDIR}
    fi

    off
    get_ip_pair_list
    start_all_server
    start_all_send_pps_netperf_udp64
    get_all_sar
    show_all_send_pps_udp64
}



#功能入口：多机接收测试netperf udp 64
function all_ecs_recv_pps_netperf_udp64()
{
    if [ ! -d ./${DIR}/${SUBDIR} ];then
      mkdir -p ./${DIR}/${SUBDIR}
    fi

    off
    get_ip_pair_list
    start_all_server
    start_all_recv_pps_netperf_udp64
    get_all_sar
    show_all_recv_pps_udp64
}



#功能入口:flavor最大发送带宽,netperf TCP 1440
function one_ecs_flavor_send_bw_netperf()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_pps_netserver
    flavor_send_bw_netperf
    pingloss
    sar
}


#功能入口：flaovr最大接收带宽,netperf TCP 1440
function one_ecs_flavor_recv_bw_netperf()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_pps_netserver
    flavor_recv_bw_netperf
    pingloss
    sar
}


#功能入口：flavor最大发送带宽netperf TCP 64
function one_ecs_flavor_bw_netperf_tcp64()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_pps_netserver
    flavor_send_bw_netperf_tcp64
    pingloss
    sar
}


#功能入口:发送pps,iperf3 UDP 64
function one_ecs_flavor_send_pps_iperf3()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_flavor_iperf3_server
    flavor_send_pps_iperf3
    sar
}


#功能入口:发送PPS,netperf UDP 64
function one_ecs_flavor_send_pps_netperf()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_pps_netserver
    flavor_send_bw_netperf
    pingloss
    sar
}


#功能入口:netperf接收PPS,netperf udp 64
function one_ecs_flavor_recv_pps_netperf()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_pps_netserver
    flavor_recv_pps_netperf_udp64
    pingloss
    sar
}


#功能入口:接收pps
function one_ecs_flavor_recv_pps_iperf3()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_flavor_iperf3_server
    flavor_recv_pps_iperf3
    sar
}


#功能入口:双向pps
function one_ecs_flavor_dual_pps_iperf3()
{
    off
    read_FLAVOR_PORTeilian_ip
    start_flavor_iperf3_server
    flavor_dual_pps_iperf3
    pingloss
    sar
}


#功能入口：移除iperf3.1，拷贝iperf3.3
function install_iperf3_3()
{
    get_ip_pair_list
    copy_iperf3_3
}



#----------------------------------------------------------------------------------------------------
#全局入口:main函数
function main()
{
    #创建新log
    create_new_real_log

    ####################  1v1  ####################
    #单网卡带宽
    one_to_one_bw_netperf

    #单网卡收+发带宽
    one_to_one_dual_bw_netperf

    #多网卡发送带宽
    one_to_one_multi_port_send_bw_netperf

    #多网卡发送PPS
    one_to_one_multi_port_send_pps_netperf


    ####################  15v15  ####################
    #15v15发送带宽
    all_ecs_send_bw_netperf_tcp1440

    #15v15接收带宽
    all_ecs_recv_bw_netperf_tcp1440

    #15v15发送PPS
    all_ecs_send_pps_netperf_udp64

    #15v15接收PPS
    all_ecs_recv_pps_netperf_udp64

    
    ####################  1v8  ####################
    #发送PPS netperf
    one_ecs_flavor_send_pps_netperf

    #接收PPS netperf
    one_ecs_flavor_recv_pps_netperf

    #最大发送带宽 netperf
    one_ecs_flavor_send_bw_netperf

    #最大接收带宽 netperf
    one_ecs_flavor_recv_bw_netperf

    #发送PPS-iperf3
    one_ecs_flavor_send_pps_iperf3
    
    #接收PPS-iperf3
    one_ecs_flavor_recv_pps_iperf3

    #双向PPS iperf3
    one_ecs_flavor_dual_pps_iperf3

    #安装iperf 3.3
    install_iperf3_3
}

main
#off
echo -e "finish"


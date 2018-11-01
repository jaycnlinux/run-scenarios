#!/bin/bash

function off()
{
    pkill iperf3
    pkill netserver
    pkill memcached
    pkill qperf
    for i in `ps -ef | grep -i '\/server ' | grep -v grep | awk '{print $2}'`;do
        kill -9 $i
        sleep 0.1
    done
    pkill nginx
    nginx -s stop 2>/dev/null 1>/dev/null
    for i in `ps -ef | grep -i construct | grep -v grep | awk '{print $2}'`;do
        kill -9 $i
        sleep 0.1
    done
    sleep 1
    pkill iperf3
    pkill netserver
    pkill memcached
    pkill qperf
    for i in `ps -ef | grep -i '\/server ' | grep -v grep | awk '{print $2}'`;do
        kill -9 $i
        sleep 0.1
    done
    pkill nginx
    nginx -s stop 2>/dev/null 1>/dev/null
    for i in `ps -ef | grep -i construct | grep -v grep | awk '{print $2}'`;do
        kill -9 $i
        sleep 0.1
    done
    sleep 1
    
}

function start_server()
{
    echo "start qperf"
    qperf &

    echo "start netserver"
    netserver

    echo "start nginx"
    nginx

    echo "start memcached"
    memcached -p 22122 -d -u root

    echo "start meinian udp server"
    cd /root/ConstructTest/Linux/
    sh server.sh 2>/dev/null 1>/dev/null &
    cd /root/
    
    echo "start netserver 7001 to 7016"
    for i in `seq 7001 7016`;do
        netserver -p $i 2>/dev/null 1>/dev/null
    done

    echo "start iperf3 server 8001 to 8016"
    for i in `seq 8001 8016`;do
        iperf3 -s -p $i -i 60 2>/dev/null 1>/dev/null &
    done

    echo "start memcached 9001 to 9004"
    for i in `seq 9001 9004`;do
        memcached -p $i -d -u root 2>/dev/null 1>/dev/null
    done

    echo "start c1000k server port begin 11000 "
    base_port=11000
    echo -e "c1000k port \c"
    for i in `seq 1 16`;do
        port=$(($base_port + ($i-1)*2000))
        /root/server $port 2>/dev/null 1>/dev/null &
        echo -e "$port \c"
    done
    echo ""
}


function main()
{
    off
    start_server
}


####################  主函数main  ##################
main

echo -e "start success!"

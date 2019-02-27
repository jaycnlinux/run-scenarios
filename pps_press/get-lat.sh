#!/bin/bash


host=""

sleep 10
echo -e "\n\n"
echo ">>>> ping $host -c 60"
ping $host -c 60 | grep -E -i "avg|loss"


sleep 10
echo -e "\n\n"
echo ">>>> qperf udp 64 to $host"
qperf $host -t 60 -m 64 -vu udp_lat


sleep 10
echo -e "\n\n"
echo ">>>> qperf tcp 64 to $host"
qperf $host -t 60 -m 64 -vu tcp_lat
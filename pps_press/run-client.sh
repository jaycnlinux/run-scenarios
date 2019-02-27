#!/bin/bash


host=""
bw=""

pkill iperf3;sleep 2
pkill iperf3;sleep 2

for i in `seq 7001 7032`;do
    iperf3 -c $host -p $i -u -b ${bw}M -l 64 -t 1200 -i 60 2>/dev/null 1>/dev/null &
done

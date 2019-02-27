#!/bin/bash

pkill iperf3;sleep 2
pkill iperf3;sleep 2

for i in `seq 7001 7064`;do
    iperf3 -s -p $i -i 60 2>/dev/null 1>/dev/null &
done
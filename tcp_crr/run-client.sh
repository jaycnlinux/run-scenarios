#!/bin/bash

host="172.31.210.46"
TIME=20
baseport=7000
count=32

if [ ! $1 ];then
    echo "thread=NULL, set thread=$count"
else
    count=$1
fi

pkill netperf
sleep 2
pkill netperf
sleep 2
rm -f crr*.log

for i in `seq 1 $count`;do
    port=$(($i + $baseport))
    cmd="netperf -H $host -p $port -t TCP_CRR -l $TIME -- -r 64" 
    echo $cmd
    eval $cmd > crr_$i.log &
done

echo "sleep ${TIME}s"
for i in `seq 1 $TIME`;do
    echo -e "$i \c"
    sleep 1
done
sleep 5
echo

sum_crr=0
for i in `cat crr*.log | grep " 64 " | awk '{print $6}'`;do
    echo $i
    sum_crr=`awk -v a=$sum_crr -v b=$i 'BEGIN{printf "%.2f",(a+b)}'`
done
echo "--------"
echo "sum_crr=$sum_crr"
echo -e "total-records\t"
cat crr*.log | grep " 64 " | wc -l



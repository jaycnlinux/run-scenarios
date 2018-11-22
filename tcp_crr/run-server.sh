#!/bin/bash


pkill netserver
sleep 2 
pkill netserver

for i in `seq 7001 7064`;do
    netserver -p $i
done 

ps -ef | grep netserver | grep -v grep 
ps -ef | grep netserver | grep -v grep | wc -l

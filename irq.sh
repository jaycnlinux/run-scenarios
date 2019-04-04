

service irqbalance stop

cpu=0
for i in `cat /proc/interrupts | grep input | awk -F [:' '] '{print $2}'`;do
    cpu=$(($cpu%64))
    echo $cpu > /proc/irq/$i/smp_affinity_list
    ((cpu++))
done

cpu=0
for i in `cat /proc/interrupts | grep output | awk -F [:' '] '{print $2}'`;do
    cpu=$(($cpu%64))
    echo $cpu > /proc/irq/$i/smp_affinity_list
    ((cpu++))
done

for i in `seq 0 31`;do
    echo 0 > /sys/class/net/eth0/queues/rx-$i/rps_cpus
    echo 0 > /sys/class/net/eth0/queues/rx-$i/rps_flow_cnt
    echo 0 > /sys/class/net/eth0/queues/tx-$i/xps_cpus
done

echo 0 > /proc/sys/net/core/rps_sock_flow_entries

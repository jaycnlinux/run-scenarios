host="172.31.11.118"


function off()
{
    echo "pkill netperf"
    pkill netperf 1>/dev/null 2>/dev/null;sleep 0.1;pkill netperf 1>/dev/null 2>/dev/null
    pkill sar 1>/dev/null 2>/dev/null;sleep 0.1;pkill sar 1>/dev/null 2>/dev/null
}


function test_16_flow()
{
    seq=$1
    echo "netperf to $host 16 flows"
    for i in `seq 7001 7016`;do
        netperf -H $host -p $i -t TCP_STREAM -l 1200 -- -m 1440 2>/dev/null 1>/dev/null &
    done
    sleep 30
    echo "sar start"
    sar -n DEV 1 60 > 16flow_${seq}.txt
}


function test_1_flow()
{
    seq=$1
    echo "netperf to $host 1 flows"
    netperf -H $host -p 7001 -t TCP_STREAM -l 1200 -- -m 1440 2>/dev/null 1>/dev/null &
    sleep 30
    echo "sar start"
    sar -n DEV 1 60 > 1_flow_${seq}.txt
}


function main()
{
    for i in `seq 1 5`;do
        echo -e "\n\n========Round $i========"
        off
        test_1_flow $i
        off
        sleep 30
    done
    
    for i in `seq 1 5`;do
        echo -e "\n\n========Round $i========"
        off
        test_16_flow $i
        off
        sleep 30
    done
    
}

main
echo "finish"

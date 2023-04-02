#!/bin/bash
source /etc/xx/conf.d/base.conf
[ -e $wanconf ] && source $wanconf || exit 1
[ -e $networkconf ] && source $networkconf || exit 1

[ -e $run_path/qos/tmp ] || mkdir -p $run_path/qos/tmp
Interfaces=()

for f in `ls $cli_conf/qos/class*.conf 2>/dev/null`
do
    tmp=${f##*class}
    classid=${tmp%%.*}
    [ $classid -gt 10 -a $classid -le 254 ] 2>/dev/null || continue

    class_id=1:${classid}
    class_type=$(awk -F'=' '$1=="class_type_conf"{print $2}' $f 2>/dev/null)
    interfaces=()

    if [ "$class_type" == wan ];then
        interfaces=($wan1_interface $wan2_interface $lte_interface)
    elif [ "$class_type" == interconnection ];then
        for tunnel_id in $(ls /usr/local/xx/conf.d/tunnel 2>/dev/null)
        do
            interfaces="$interfaces ipip${tunnel_id}s ipip${tunnel_id}i"
        done
        interfaces=($interfaces)
    elif [[ "$class_type" =~ ^vlan[0-9]+$ ]];then
        vlan="br-i$class_type"
        [ -e /sys/class/net/$vlan ] || exit 3
        [ -e "/usr/local/xx/conf.d/qos/$vlan" ] || add_qdisc $vlan
        interfaces=($vlan)
    else
        exit 1
    fi
    Interfaces=(${interfaces[*]} ${Interfaces[*]})

    sum_tx=0
    for interface in  ${interfaces[*]}
    do
        if [ -n "$interface" ] && [ -e /sys/class/net/$interface ];then
            if [ ! -e $run_path/qos/tmp/$interface ];then
                tc -s class show dev $interface|awk -v class='' '/^class htb/ { class=$3 } /Sent/ { print class " " $2 } ' > $run_path/qos/tmp/$interface
            fi
        else
            continue
        fi

        while read line
        do
            tmp=($line)
            tmp_id=${tmp[0]}
            tmp_tx=${tmp[1]}

            if [ "$class_id" == "$tmp_id" ];then
                sum_tx=$(($sum_tx + $tmp_tx))
                break
            else
                continue
            fi

        done < $run_path/qos/tmp/$interface
    done
    [ -e $run_path/qos/${classid} ] && mv $run_path/qos/${classid} $run_path/qos/${classid}.1
    echo $sum_tx > $run_path/qos/${classid}
done


for interface in ${Interfaces[*]}
do
    [ -e $run_path/qos/tmp/$interface ] && mv $run_path/qos/tmp/$interface $run_path/qos/tmp/${interface}.1
done

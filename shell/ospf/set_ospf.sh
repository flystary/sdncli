#!/bin/bash

ARGS=`getopt -o h: -l "enable:, router-id:, bgp-redistribute:, bgp-route-map:, bgp-metric-type:, static-redistribute:, static-route-map:, static-metric-type:," -n "$0" -- "$@"`
eval set -- "${ARGS}"
if [ $? != 0 ]; then
    echo "Terminating..."
    exit 1
fi

while true
do
    case $1 in
        --enable)                   enable=$2; shift 2 ;;
        --router-id)                router_id=$2; shift 2 ;;
        --bgp-redistribute)         bgp_redistribute=$2; shift 2;;
        --bgp-route-map)            bgp_route_map=$2; shift 2;;
        --bgp-metric-type)          bgp_metric_type=$2; shift 2;;
        --static-redistribute)      static_redistribute=$2; shift 2;;
        --static-route-map)         static_route_map=$2; shift 2;;
        --static-metric-type)       static_metric_type=$2; shift 2;;
        --)       shift;   break ;;
        *)        echo "Internal error!"; exit 1 ;;
    esac
done

source /etc/svxnetworks/conf.d/base.conf
source $cli_root/function.sh

[ -n "$enable" ] || exit 1

if [ "$enable" == "false" ]; then
vtysh >/dev/null <<EOF
configure terminal
no router ospf
end
write
quit
EOF
    sync
    [ `grep -c "router ospf" $ospfd_conf 2>/dev/null` -ne 0 ] && exit 1
fi

if [ $(awk -v id=${router_id} '$1=="ospf"&&$2=="router-id"&&$3==id' $ospfd_conf 2>/dev/null|wc -l) -eq 0 ];then
    do_ospf_route_id="ospf router-id $router_id"
else
    do_ospf_route_id=
fi

[ -n "$bgp_redistribute" ]    || bgp_redistribute=false
[ -n "$static_redistribute" ] || static_redistribute=false

b_route_map_tmp=
s_route_map_tmp=
b_metric_tyep_tmp=
s_metric_type_tmp=
[ -n "$bgp_route_map" ] && {
    b_route_map_tmp="route-map $bgp_route_map"
}

[ -n "$static_route_map" ] && {
    s_route_map_tmp="route-map $static_route_map"
}

[ -n "$bgp_metric_type" ] && {
    b_metric_tyep_tmp="metric-type $bgp_metric_type"
}

[ -n "$static_metric_type" ] && {
    s_metric_type_tmp="metric-type $static_metric_type"
}


# redistribute bgp metric-type 1 route-map rm-glink91

if [ "$bgp_redistribute" == "true" ]; then
    do_redistribute_bgp="redistribute bgp $b_metric_tyep_tmp $b_route_map_tmp"
else
    do_redistribute_bgp="no redistribute bgp"
fi

if [ "$static_redistribute" == "true" ]; then
    do_redistribute_static="redistribute static $s_metric_type_tmp $s_route_map_tmp"
else
    do_redistribute_static="no redistribute static"
fi

if [ $(awk '$1=="passive-interface"&&$2=="default"' $ospfd_conf 2>/dev/null|wc -l) -eq 0 ];then
    do_passive_interface_default="passive-interface default"
else
    do_passive_interface_default=
fi

if [ "$enable" == "true" ]; then
vtysh >/tmp/vtysh_ospf.result <<EOF
configure terminal
router ospf
$do_ospf_route_id
$do_redistribute_bgp
$do_redistribute_static
$do_passive_interface_default
end
write
quit
EOF
sync

    #cidr_grep=${router_id//\./\\\.}
    [ `grep -c "ospf router-id $router_id" $ospfd_conf 2>/dev/null` -ne 1 ] && exit 1

    if [ "$bgp_redistribute" == "true" ]; then
        [ `grep -c "redistribute bgp" $ospfd_conf 2>/dev/null` -eq 0 ] && exit 1
    else
        [ `grep -c "redistribute bgp" $ospfd_conf 2>/dev/null` -ne 0 ] && exit 1
    fi

    if [ "$static_redistribute" == "true" ]; then
        [ `sed  -n '/router ospf/,/^!/p' $ospfd_conf|grep -c "redistribute static"` -eq 0 ] && exit 1
    else
        [ `sed  -n '/router ospf/,/^!/p' $ospfd_conf|grep -c "redistribute static"` -ne 0 ] && exit 1
    fi

    [ $(grep -icE 'locker by|Command incomplete|Unknown command|failed' /tmp/vtysh_ospf.result) -eq 0 ] && exit 0 || exit 3

fi

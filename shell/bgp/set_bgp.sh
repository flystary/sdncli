#!/bin/bash

ARGS=`getopt -o h: -l "local-as:, router-id:, ospf-redistribute:, ospf-route-map:, static-redistribute:, static-route-map:," -n "$0" -- "$@"`
eval set -- "${ARGS}"
if [ $? != 0 ]; then
    echo "Terminating..."
    exit 1
fi

while true
do
    case $1 in
        --local-as)             local_as=$2;  shift 2 ;;
        --router-id)            router_id=$2; shift 2 ;;
        --ospf-redistribute)    ospf_redistribute=$2; shift 2;;
        --ospf-route-map)       ospf_route_map=$2; shift 2;;
        --static-redistribute)  static_redistribute=$2; shift 2;;
        --static-route-map)     static_route_map=$2; shift 2;;
        --)          shift;        break ;;
        *)           echo "Internal error!"; exit 1 ;;
    esac
done

[ "$local_as" == null ] && local_as=
#[ $local_as -ge 1 $local_as -le 65535 ] 2>/dev/null || exit 1
source /etc/svxnetworks/conf.d/base.conf
source $cli_root/function.sh

[ ! -n "$ospf_redistribute" ] && ospf_redistribute=false
[ ! -n "$static_redistribute" ] && static_redistribute=false

old_as=$(awk '$1=="router"&&$2=="bgp"{print $3}' $bgpd_conf 2>/dev/null)

[ -z "$old_as" -a -z "$local_as" ] && exit 2
[ -z "$local_as" ] && local_as=$old_as

[ -n "$old_as" ] && [ $old_as -ne $local_as ] && del_old="no router bgp $old_as"

[ -n "$router_id" ] && set_route_id="bgp router-id $router_id"

o_route_map_tmp=
s_route_map_tmp=
[ -n "$ospf_route_map" ] && {
    o_route_map_tmp="route-map $ospf_route_map"
}

[ -n "$static_route_map" ] && {
    s_route_map_tmp="route-map $static_route_map"
}

if [ "$ospf_redistribute" == "true" ]; then
    do_redistribute_ospf="redistribute ospf $o_route_map_tmp"
else
    do_redistribute_ospf="no redistribute ospf"
fi

if [ "$static_redistribute" == "true" ]; then
    do_redistribute_static="redistribute static $s_route_map_tmp"
else
    do_redistribute_static="no redistribute static"
fi

vtysh >/tmp/vtysh_bgp.result <<EOF
configure terminal
$del_old
router bgp $local_as
no bgp ebgp-requires-policy
no bgp network import-check
$set_route_id
timers bgp 3 9
$do_redistribute_ospf
$do_redistribute_static
end
clear ip bgp * soft
write
quit
EOF

sync

[ $(awk -v as=$local_as '$1=="router"&&$2=="bgp"&&$3==as' $bgpd_conf 2>/dev/null |wc -l) -ne 1 ] && exit 1
[ $(awk -v i=$router_id '$1=="bgp"&&$2=="router-id"&&$3==i' $bgpd_conf 2>/dev/null |wc -l) -ne 1 ] && exit 1

if [ "$ospf_redistribute" == "true" ]; then
    [ `grep -c "redistribute ospf" $bgpd_conf 2>/dev/null` -eq 0 ] && exit 1
else
    [ `grep -c "redistribute ospf" $bgpd_conf 2>/dev/null` -ne 0 ] && exit 1
fi

if [ "$static_redistribute" == "true" ]; then
    [ `sed  -n '/address-family ipv4 unicast/,/^!/p' $ospfd_conf|grep -c "redistribute static"` -eq 0 ] && exit 1
else
    [ `sed  -n '/address-family ipv4 unicast/,/^!/p' $ospfd_conf|grep -c "redistribute static"` -ne 0 ] && exit 1
fi

[ $(grep -icE 'locker by|Command incomplete|Unknown command|failed' /tmp/vtysh_bgp.result) -eq 0 ] || exit 3

exit 0

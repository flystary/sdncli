#!/bin/bash

while getopts "f:" opt; do
    case $opt in
        f) filename=$OPTARG ;;
        *) exit 1 ;;
    esac
done

cmd_prefix='bgp'

#cmd_prefix='ip'

[ ! -e "$filename" ] 2>/dev/null && exit 1
typeset -l asname
typeset -l pflname
typeset -l rmname

typeset -l matchAsPath
typeset -l matchPrefix

source /etc/svxnetworks/conf.d/base.conf
dyncmdline=/tmp/vtysh_dynamic_route.cmd
echo "configure terminal" > $dyncmdline

error=false
dynroute_path="/usr/local/svxnetworks/conf.d/dynroute"
[ -e $dynroute_path ] || mkdir -p $dynroute_path
as_path_conf=$dynroute_path/dynAsPath.conf
prefix_list_conf=$dynroute_path/dynPrefixList.conf
route_map_conf=$dynroute_path/dynRouteMap.conf

as_tmpfile=/tmp/dyn_aspath.tmp
pfl_tmpfile=/tmp/dyn_prefixlist.tmp
rm_tmpfile=/tmp/dyn_routemap.tmp
rm -f $as_tmpfile $pfl_tmpfile $rm_tmpfile

jsonfilter -i $filename -e '@.*' 2>/dev/null || {
    echo "json解析错误"
    exit 5
}

as_counter=$(jsonfilter -i $filename -e '@.asPaths.*' |wc -l) || {
    echo "解析asPath错误"
    exit 6
}
pfl_counter=$(jsonfilter -i $filename -e '@.prefixLists.*' |wc -l) || {
    echo "解析prefixList错误"
    exit 7
}
rm_counter=$(jsonfilter -i $filename -e '@.routeMaps.*' |wc -l) || {
    echo "解析routeMap错误"
    exit 8
}

sync_file='/usr/local/svxnetworks/conf.d/sync_dynamic_route.json'
newroutemaps=()

[ $as_counter -gt 0 ] && for i in $(seq 0 $(($as_counter-1)))
do
    line=$(($i+1))
    tmp=$(jsonfilter -i $filename -e "@.asPaths[$i]") &&\
    action=$(echo $tmp |jsonfilter -e '@.action') &&\
    value=$(echo $tmp |jsonfilter -e '@.actionValue') &&\
    name=$(echo $tmp |jsonfilter -e '@.name') || {
        echo "第${line}条规则asPath json格式错误"
        error=true
        break
    }

    [ -n "$name" ] || exit 9
    # 去掉多余空格
    value=$(echo $value)

    [ -n "$action" ] || action=null
    [ -n "$value" ]  || value=null
    echo $name $action $value >> $as_tmpfile
done

[ $pfl_counter -gt 0 ] && for i in $(seq 0 $(($pfl_counter-1)))
do
    line=$(($i+1))
    tmp=$(jsonfilter -i $filename -e "@.prefixLists[$i]") &&\
    sequence=$(echo $tmp |jsonfilter -e '@.seq') &&\
    action=$(echo $tmp |jsonfilter -e '@.action') &&\
    cidr=$(echo $tmp |jsonfilter -e '@.cidr') &&\
    name=$(echo $tmp |jsonfilter -e '@.name') || {
        echo "第${line}条规则prefixLists json格式错误"
        error=true
        break
    }

    [ -n "$name" ]   || exit 9
    [ $sequence -gt 0 ] || exit 9


    [ -n "$action" ] || action=null
    [ -n "$cidr" ]   || cidr=null

    echo $name $sequence $action $cidr >> $pfl_tmpfile
done

[ $rm_counter -gt 0 ] && for i in $(seq 0 $(($rm_counter-1)))
do
    line=$(($i+1))
    tmp=$(jsonfilter -i $filename -e "@.routeMaps[$i]") &&\
    sequence=$(echo $tmp |jsonfilter -e '@.seq') &&\
    action=$(echo $tmp |jsonfilter -e '@.action') &&\
    name=$(echo $tmp |jsonfilter -e '@.name') || {
        echo "第${line}条规则routeMap json格式错误"
        error=true
        break
    }

    [ -n "$action" ]  || action=null
    [ -n "$name" ]    || exit 9
    [ $sequence -gt 0 ] || exit 9

    set_counter=$(echo $tmp|jsonfilter -e '@.setList[*]' |wc -l)
    match_counter=$(echo $tmp|jsonfilter -e '@.matchList[*]' |wc -l)

    matchAsPath=
    matchPrefix=
    metric=
    localPreference=
    asPathPrepend=()
    [ $match_counter -gt 0 ] && for i in $(seq 0 $(($match_counter-1)))
    do
        line=$(($i+1))
        tmprmm=$(echo $tmp|jsonfilter -e "@.matchList[$i]") &&\
        match_type=$(echo $tmprmm |jsonfilter -e '@.matchType') &&\
        match_value=$(echo $tmprmm |jsonfilter -e '@.matchValue') ||{
            echo "第${line}条规则matchList json格式错误"
            error=true
            break
        }
        [ "$match_type" == "as-path" ]     && matchAsPath=$match_value
        [ "$match_type" == "prefix-list" ] && matchPrefix=$match_value
    done

    [ $set_counter -gt 0 ] && for i in $(seq 0 $(($set_counter-1)))
    do
        line=$(($i+1))
        tmprms=$(echo $tmp |jsonfilter -e "@.setList[$i]") &&\
        set_type=$(echo $tmprms |jsonfilter -e '@.setType') &&\
        set_value=$(echo $tmprms |jsonfilter -e '@.setValue') || {
            echo "第${line}条规则setList json格式错误"
            error=true
            break
        }
        [ "$set_type" == "metric" ] &&  metric=$set_value
        [ "$set_type" == "local-preference" ] && localPreference=$set_value
        # 去掉多余空格
        [ "$set_type" == "as-path-prepend" ]  && asPathPrepend=$set_value
    done

    # 判断下发的是否存在asPath/prefixList的数据中
    [ $(awk -v n=$matchAsPath '$1==n {print $0}' $as_tmpfile |wc -l) -ne 0 ]   || {
        echo "$matchAsPath 在asPaths中未找到此数据"
        exit 3
    }
    [ $(awk -v n=$matchPrefix '$1==n {print $0}' $pfl_tmpfile | wc -l) -ne 0 ] || {
        echo "$matchAsPath 在prefixLists中未找到此数据"
        exit 3
    }

    [ -n "$matchAsPath" ]     || matchAsPath=null
    [ -n "$matchPrefix" ]     || matchPrefix=null
    [ -n "$metric" ]          || metric=0
    [ -n "$localPreference" ] || localPreference=0
    [ -n "$asPathPrepend" ]   || asPathPrepend=null

    onlyNs="${name}|$sequence"

    newroutemaps+=(${onlyNs})

    echo $onlyNs $name $action $sequence $matchAsPath $matchPrefix $localPreference $metric $asPathPrepend >> $rm_tmpfile
done

# 删除AsPath
# name action value
while read line
do
    tmp=($line)
    [ ${#line[*]} -lt 3 ] && continue
    name=${tmp[0]}
    action=${tmp[1]}
    value=${tmp[*]:2}
    # 老配置里有，新配置没有的as号要删除
    [ $(awk -F'/' -v p="$name $action $value" '$1==p{print 1}' $as_tmpfile |wc -l) -eq 0 ] && \
        echo no $cmd_prefix as-path access-list $name $action $value >> $dyncmdline
done < $as_path_conf

# 删除PrefixList
# name sequence action cidr
while read line
do
    tmp=($line)
    name=${tmp[0]}
    sequence=${tmp[1]}
    action=${tmp[2]}
    cidr=${tmp[3]}
    # 老配置里有，新配置没有的as号要删除
    [ $(awk -F '|' -v p="$name $sequence $action $cidr" '$1==p{print 1}' $pfl_tmpfile |wc -l) -eq 0 ] && \
        echo no ip prefix-list $name seq $sequence $action $cidr >> $dyncmdline
done < $prefix_list_conf

# 增加AsPath
while read line
do
    tmp=($line)
    name=${tmp[0]}
    action=${tmp[1]}
    value=${tmp[*]:2}
    [ $(awk -F'/' -v p="$name $action $value" '$1==p{print 1}' $as_path_conf |wc -l) -eq 0 ] || continue
    echo $cmd_prefix as-path access-list $name $action $value >> $dyncmdline
done < $as_tmpfile

# 增加PrefixList
while read line
do
    tmp=($line)
    name=${tmp[0]}
    sequence=${tmp[1]}
    action=${tmp[2]}
    cidr=${tmp[3]}
    [ $(awk -F '|' -v p="$name $sequence $action $cidr" '$1==p{print 1}' $prefix_list_conf |wc -l) -eq 0 ] || continue
    echo ip prefix-list $name seq $sequence $action $cidr >> $dyncmdline
done < $pfl_tmpfile

# RouteMap
del_routemaps=()
same_routemaps=()
add_routemaps=()

if [ -e $route_map_conf ];then
    oldroutemaps=($(awk '{print $1}' $route_map_conf 2>/dev/null))
    # del
    for onlyns_o in ${oldroutemaps[*]}
    do
        exist=0
        for onlyns_n in ${newroutemaps[*]}
        do
            [ "$onlyns_o" == "$onlyns_n" ] && {
                exist=1
                break
            }
        done
        [ $exist -eq 0 ] && del_routemaps+=(${onlyns_o})
    done

    # same
    for onlyns_o in ${oldroutemaps[*]}
    do
        exist=0
        for onlyns_d in ${del_routemaps[*]}
        do
            [ "$onlyns_o" == "$onlyns_d" ] && {
                exist=1
                break
            }
        done
        [ $exist -eq 0 ] && same_routemaps+=(${onlyns_o})
    done

    # add
    for onlyns_n in ${newroutemaps[*]}
    do
        exist=0
        for onlyns_o in ${oldroutemaps[*]}
        do
            [ "$onlyns_n" == "$onlyns_o" ] && {
                exist=1
                break
            }
        done
        [ $exist -eq 0 ] && add_routemaps+=(${onlyns_n})
    done
else
    add_routemaps=(${newroutemaps[*]})
fi

# 删除
for onlyns in ${del_routemaps[*]}
do
    tmp=($(awk -v ns=$onlyns '$1==ns{print $0}' $route_map_conf 2>/dev/null))
    # $onlyNs $name $action $sequence $matchAsPath $matchPrefix $localPreference $metric $asPathPrepend
    onlyns=${tmp[0]}
    name=${tmp[1]}
    action=${tmp[2]}
    sequence=${tmp[3]}

    [ -n "$name" ] && [ "$name" != null ] &&  [ -n "$action" ] && [ "$action" != null ] && [ -n "$sequence" ] && [ $sequence -ge 0 ] || continue

    echo no route-map $name $action $sequence >> $dyncmdline
done

# 比较
for onlyns in ${same_routemaps[*]}
do
    # awk -v ns=$onlyns '$1==ns{print $0}' $rm_tmpfile 2>/dev/null | while read -a line
    tmp=($(awk -v ns=$onlyns '$1==ns{print $0}' $rm_tmpfile 2>/dev/null))
    onlyns=${tmp[0]}
    name=${tmp[1]}
    action=${tmp[2]}
    sequence=${tmp[3]}
    matchAsPath=${tmp[4]}
    matchPrefix=${tmp[5]}
    localPreference=${tmp[6]}
    metric=${tmp[7]}
    asPathPrepend=${tmp[*]:8}

    [ -n "$name" ] && [ "$name" != null ] &&  [ -n "$action" ] && [ "$action" != null ] && [ -n "$sequence" ] && [ $sequence -ge 0 ] || continue

    echo route-map $name $action $sequence >> $dyncmdline

    if [ "$matchAsPath" != null ];then
        echo match as-path $matchAsPath >> $dyncmdline
    else
        echo no match as-path $matchAsPath >> $dyncmdline
    fi

    if [ "$matchPrefix" != null ];then
        echo match ip address prefix-list $matchPrefix >> $dyncmdline
    else
        echo no match ip address prefix-list >> $dyncmdline
    fi

    if [ $localPreference -gt 0 ];then
        echo set local-preference $localPreference >> $dyncmdline
    else
        echo no set local-preference >> $dyncmdline
    fi

    if [ $metric -gt 0 ];then
        echo set metric $metric >> $dyncmdline
    else
        echo no set metric >> $dyncmdline
    fi

    if [ "$asPathPrepend" != null ];then
        echo set as-path prepend $asPathPrepend >> $dyncmdline
    else
        echo no set as-path prepend >> $dyncmdline
    fi
done

# 新增
for onlyns in ${add_routemaps[*]}
do
    # awk -v ns=$onlyns '$1==ns{print $0}' $$rm_tmpfile 2>/dev/null | while read -a line
    tmp=($(awk -v ns=$onlyns '$1==ns{print $0}' $rm_tmpfile 2>/dev/null))
    onlyns=${tmp[0]}
    name=${tmp[1]}
    action=${tmp[2]}
    sequence=${tmp[3]}
    matchAsPath=${tmp[4]}
    matchPrefix=${tmp[5]}
    localPreference=${tmp[6]}
    metric=${tmp[7]}
    asPathPrepend=${tmp[*]:8}

    [ -n "$name" ] && [ "$name" != null ] &&  [ -n "$action" ] && [ "$action" != null ] && [ -n "$sequence" ] && [ $sequence -ge 0 ] || continue

    echo route-map $name $action $sequence >> $dyncmdline

    [ "$matchAsPath" != null ] && {
        echo match as-path $matchAsPath >> $dyncmdline
    }
    [ "$matchPrefix" != null ] && {
        echo match ip address prefix-list $matchPrefix >> $dyncmdline
    }
    [ $localPreference -gt 0 ] && {
        echo set local-preference $localPreference >> $dyncmdline
    }
    [ $metric -gt 0 ] && {
        echo set metric $metric >> $dyncmdline
    }
    [ "$asPathPrepend" != null ] && {
        echo set as-path prepend $asPathPrepend >> $dyncmdline
    }
done

echo end >> $dyncmdline
echo 'clear ip bgp * soft' >> $dyncmdline
echo write >> $dyncmdline
echo quit  >> $dyncmdline

vtysh &>/tmp/vtysh.result < $dyncmdline
sync

# 保存旧配置
cp $as_tmpfile  $as_path_conf
cp $pfl_tmpfile $prefix_list_conf
cp $rm_tmpfile  $route_map_conf

# 删除临时
rm -f $as_tmpfile $pfl_tmpfile $rm_tmpfile

[ `grep -icE 'locker by|Command incomplete|Unknown command|failed' /tmp/vtysh.result` -eq 0 ] || exit 3

rm -f $dyncmdline
/bin/mv $filename $sync_file

sync
exit 0

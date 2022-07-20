#!/usr/bin/bash
series=$1

set -x

build_out=$(./tools/build.sh $series)
hash=$(echo $build_out | jq -r .state_hash)
deb=$(echo $build_out | jq -r .debs[] | grep tools)
name=ua-$series-$hash

if [ -n "$VM" ]; then
    flags="--vm"
fi

lxc delete $name --force
lxc launch ubuntu-daily:$series $name $flags
sleep 5
if [ -n "$VM" ]; then
    echo "vms take a while before the agent is ready"
    sleep 30
fi
lxc file push $deb $name/tmp/ua.deb

if [ -n "$SHELL_BEFORE" ]; then
    set +x
    echo
    echo
    echo "New version of pro has not been installed yet."
    echo "After you exit the shell we'll upgrade pro and bring you right back."
    echo
    set -x
    lxc exec $name bash
fi

lxc exec $name -- dpkg -i /tmp/ua.deb
lxc shell $name

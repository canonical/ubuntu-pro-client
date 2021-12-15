#!/usr/bin/bash
series=$1

set -x

build_out=$(./tools/build.sh $series)
hash=$(echo $build_out | jq -r .state_hash)
deb=$(echo $build_out | jq -r .debs[] | grep tools)
name=ua-$series-$hash

lxc delete $name --force
lxc launch ubuntu-daily:$series $name
sleep 5
lxc file push $deb $name/tmp/ua.deb

if [ -n "$SHELL_BEFORE" ]; then
    set +x
    echo
    echo
    echo "New version of ua has not been installed yet."
    echo "After you exit the shell we'll upgrade ua and bring you right back."
    echo
    set -x
    lxc exec $name bash
fi

lxc exec $name -- dpkg -i /tmp/ua.deb
lxc exec $name bash

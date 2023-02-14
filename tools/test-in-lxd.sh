#!/usr/bin/bash
set -eux

VM=${VM:-0}
series=${1:-jammy}
build_out=$(./tools/build.sh "$series")
hash=$(echo "$build_out" | jq -r .state_hash)
deb=$(echo "$build_out" | jq -r '.debs[]' | grep tools)
name=ua-$series-$hash

flags=
if [ "$VM" -ne 0 ]; then
    flags="--vm"
fi

lxc delete "$name" --force || true
lxc launch "ubuntu-daily:${series}" "$name" $flags
sleep 5
if [[ "$VM" -ne 0 ]]; then
    echo "vms take a while before the agent is ready"
    sleep 30
fi
lxc file push "$deb" "${name}/tmp/ua.deb"

lxc exec "$name" -- dpkg -i /tmp/ua.deb
lxc shell "$name"

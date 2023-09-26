#!/usr/bin/bash
#
# test-in-lxd.sh [series]
#
# Create an LXD container or vm with the current ubuntu-advantages-tool package
# built from ../

set -eux

VM=${VM:-0}
SHELL_BEFORE=${SHELL_BEFORE:-0}

series=${1:-jammy}
build_out=$(./tools/build.sh "$series")
hash=$(echo "$build_out" | jq -r .state_hash)
tools_deb=$(echo "$build_out" | jq -r '.debs[]' | grep tools)
l10n_deb=$(echo "$build_out" | jq -r '.debs[]' | grep l10n)
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
lxc file push "$tools_deb" "${name}/tmp/ua_tools.deb"
lxc file push "$l10n_deb" "${name}/tmp/ua_l10n.deb"

if [[ "$SHELL_BEFORE" -ne 0 ]]; then
    set +x
    echo
    echo
    echo "New version of pro has not been installed yet."
    echo "After you exit the shell we'll upgrade pro and bring you right back."
    echo
    set -x
    lxc exec "$name" bash
fi

lxc exec "$name" -- dpkg -i /tmp/ua_tools.deb
lxc exec "$name" -- dpkg -i /tmp/ua_l10n.deb
lxc shell "$name"

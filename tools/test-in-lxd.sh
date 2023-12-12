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
ubuntu_advantage_tools_deb=$(echo "$build_out" | jq -r '.debs.ubuntu_advantage_tools')
ubuntu_pro_client_deb=$(echo "$build_out" | jq -r '.debs.ubuntu_pro_client')
ubuntu_pro_client_l10n_deb=$(echo "$build_out" | jq -r '.debs.ubuntu_pro_client_l10n')
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
lxc file push "$ubuntu_advantage_tools_deb" "${name}/tmp/ua_tools.deb"
lxc file push "$ubuntu_pro_client_deb" "${name}/tmp/pro.deb"
lxc file push "$ubuntu_pro_client_l10n_deb" "${name}/tmp/pro_l10n.deb"

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

lxc exec "$name" -- apt install /tmp/ua_tools.deb /tmp/pro.deb /tmp/pro_l10n.deb
lxc shell "$name"

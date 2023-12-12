#!/usr/bin/bash
#
# test-in-multipass.sh [series]
#
# Create an Multipass instance with the current ubuntu-advantages-tool package
# built from ../
set -eux

SHELL_BEFORE=${SHELL_BEFORE:-0}

series=${1:-jammy}
build_out=$(./tools/build.sh "$series")
hash=$(echo "$build_out" | jq -r .state_hash)
ubuntu_advantage_tools_deb=$(echo "$build_out" | jq -r '.debs.ubuntu_advantage_tools')
ubuntu_pro_client_deb=$(echo "$build_out" | jq -r '.debs.ubuntu_pro_client')
ubuntu_pro_client_l10n_deb=$(echo "$build_out" | jq -r '.debs.ubuntu_pro_client_l10n')
name=ua-$series-$hash

multipass delete "$name" --purge || true
multipass launch "$series" --name "$name"
# Snaps won't access /tmp
cp "$ubuntu_advantage_tools_deb" ~/ua_tools.deb
cp "$ubuntu_pro_client_l10n_deb" ~/pro_l10n.deb
cp "$ubuntu_pro_client_deb" ~/pro.deb
multipass transfer ~/ua_tools.deb "${name}:/tmp/ua_tools.deb"
multipass transfer ~/pro_l10n.deb "${name}:/tmp/pro_l10n.deb"
multipass transfer ~/pro.deb "${name}:/tmp/pro.deb"
rm -f ~/ua_tools.deb
rm -f ~/ua_l10n.deb

if [[ "$SHELL_BEFORE" -ne 0 ]]; then
    set +x
    echo
    echo
    echo "New version of pro has not been installed yet."
    echo "After you exit the shell we'll upgrade pro and bring you right back."
    echo
    set -x
    multipass exec "$name" bash
fi

multipass exec "$name" -- sudo apt install /tmp/ua_tools.deb /tmp/pro.deb /tmp/pro_l10n.deb
multipass shell "$name"

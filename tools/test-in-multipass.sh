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
tools_deb=$(echo "$build_out" | jq -r '.debs[]' | grep tools)
l10n_deb=$(echo "$build_out" | jq -r '.debs[]' | grep l10n)
name=ua-$series-$hash

multipass delete "$name" --purge || true
multipass launch "$series" --name "$name"
sleep 30
# Snaps won't access /tmp
cp "$tools_deb" ~/ua_tools.deb
cp "$l10n_deb" ~/ua_l10n.deb
multipass transfer ~/ua_tools.deb "${name}:/tmp/ua_tools.deb"
multipass transfer ~/ua_l10n.deb "${name}:/tmp/ua_l10n.deb"
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

multipass exec "$name" -- sudo dpkg -i /tmp/ua_tools.deb
multipass exec "$name" -- sudo dpkg -i /tmp/ua_l10n.deb
multipass shell "$name"

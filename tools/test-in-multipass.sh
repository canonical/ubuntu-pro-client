#!/usr/bin/bash
set -eux

series=${1:-jammy}
build_out=$(./tools/build.sh "$series")
hash=$(echo "$build_out" | jq -r .state_hash)
deb=$(echo "$build_out" | jq -r '.debs[]' | grep tools)
name=ua-$series-$hash

multipass delete "$name" --purge || true
multipass launch "$series" --name "$name"
sleep 30
# Snaps won't access /tmp
cp "$deb" ~/ua.deb
multipass transfer ~/ua.deb "${name}:/tmp/ua.deb"
rm -f ~/ua.deb

multipass exec "$name" -- sudo dpkg -i /tmp/ua.deb
multipass shell "$name"

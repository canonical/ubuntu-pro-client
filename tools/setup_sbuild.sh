#!/usr/bin/bash

USAGE="
WARNING: This will create or modify chroots on your system with names matching
\"ua-\$release-\$arch\" based on the RELEASES and ARCHS environment vars.

Example Usage:
env RELEASES=\"xenial bionic\" ARCHS=\"amd64\" bash tools/setup_sbuild.sh
"

if [ -z "$RELEASES" ]; then
  echo "please set RELEASES"
  echo "$USAGE"
  exit 1
fi
if [ -z "$ARCHS" ]; then
  echo "please set ARCHS"
  echo "$USAGE"
  exit 1
fi

set -x

for release in $RELEASES
do
    for arch in $ARCHS
    do
        echo "creating chroot ua-$release-$arch"
        name="ua-$release-$arch"
        sudo sbuild-launchpad-chroot create --architecture="$arch" "--name=$name" "--series=$release"
        sudo schroot -c source:"$name" -u root -d / -- sh -c "grep -q updates /etc/apt/sources.list || echo \"deb http://archive.ubuntu.com/ubuntu/ $release-updates main restricted universe multiverse\" >> /etc/apt/sources.list"
        sudo schroot -c source:"$name" -u root -d / -- apt-get update
        sudo schroot -c source:"$name" -u root -d / -- apt-get dist-upgrade -y
        sudo schroot -c source:"$name" -u root -d / -- apt-get install -y make dpkg-dev git devscripts equivs
        sudo schroot -c source:"$name" -u root -d / -- git clone --depth 1 https://github.com/canonical/ubuntu-pro-client /var/tmp/uac
        sudo schroot -c source:"$name" -u root -d / -- make -f /var/tmp/uac/Makefile deps
        sudo schroot -c source:"$name" -u root -d / -- rm -rf /var/tmp/uac
    done
done

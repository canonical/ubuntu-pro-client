#!/usr/bin/bash
series=$1

set -x

name=ua-binary-build-$series

lxc delete $name --force
lxc launch ubuntu-daily:$series $name
sleep 5

lxc exec $name -- apt update
lxc exec $name -- apt upgrade -y
lxc exec $name -- apt install python3-pip zlib1g-dev -y
lxc exec $name -- pip3 install pyinstaller
lxc exec $name -- pyinstaller -F /usr/lib/python3/dist-packages/uaclient/cli.py
lxc exec $name -- mkdir dist/keyrings
lxc exec $name -- sh -c "cp -r /usr/share/keyrings/ubuntu-advantage-* dist/keyrings/"
# TODO: Can we rely on distro-info in a ubuntu docker image?
lxc exec $name -- apt purge ubuntu-advantage-tools -y
lxc exec $name -- ./dist/cli status
# TODO: wrapper script or something to put keyrings in right place and clean up afterwards
lxc exec $name -- bash

#!/bin/bash
set -o xtrace
apt-get update
apt-get install make
cd /tmp
ls -lh
lsb_release -a
cd /tmp/ubuntu-advantage-client
make deps
dpkg-buildpackage -us -uc
ls /tmp |grep ubuntu-advantage-tools

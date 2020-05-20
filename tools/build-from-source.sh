#!/bin/bash
set -o xtrace
apt-get update
tar -xzvf /tmp/pr_source.tar.gz --directory /tmp
cd /tmp
ls -lh
lsb_release -a
cd /tmp/ubuntu-advantage-client
apt-get install make
make deps
dpkg-buildpackage -us -uc
ls /tmp |grep ubuntu-advantage-tools

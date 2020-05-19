#!/bin/bash
set -o xtrace
apt-get update
tar -xzvf /tmp/pr_source.tar.gz --directory /tmp
cd /tmp
ls -lh
lsb_release -a
cd /tmp/ubuntu-advantage-client
git branch
apt-get install make
make deps
dpkg-buildpackage -us -uc
dpkg -i /tmp/ubuntu-advantage-tools_20.4_amd64.deb

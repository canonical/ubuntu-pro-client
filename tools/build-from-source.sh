#!/bin/bash
set -o xtrace
apt-get update
cd /home/ubuntu 
tar -xzvf pr_source.tar.gz
cd ubuntu-advantage-client/
ls -lh
pwd
lsb_release -a
git branch
apt-get install make
make deps 
dpkg-buildpackage -us -uc
dpkg -i dpkg -i ubuntu-advantage-tools_20.4_amd64.deb

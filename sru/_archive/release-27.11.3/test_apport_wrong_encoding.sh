#!/bin/bash
set -e

series=$1
name=$series-dev


function cleanup {
  lxc delete $name --force
}

function on_err {
  echo -e "Test Failed"
  cleanup
  exit 1
}

trap on_err ERR

lxc launch ubuntu-daily:$series $name
sleep 10

# Update ubuntu-advantage-tools package
lxc exec $name -- sudo apt-get update > /dev/null
lxc exec $name -- sudo apt-get upgrade -y > /dev/null
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Create a (collected) file with invalid utf-8 encoding
lxc exec $name -- touch file
lxc exec $name -- tar -zcf invalid.tar.gz file
lxc exec $name -- mv invalid.tar.gz /var/lib/ubuntu-advantage/jobs-status.json

# Error out while trying to create a bug report
echo -e "\n* Check the error in collect-logs"
echo "###########################################"
lxc exec $name -- pro collect-logs || true
echo -e "###########################################\n"

echo -e "\n* Check the error in apport-bug"
echo "###########################################"
lxc exec $name -- ubuntu-bug --save=/tmp/test1 ubuntu-advantage-tools
echo -e "###########################################\n"

# Upgrading UA to the new version
echo -e "\n* Upgrading UA to new version"
lxc exec $name --  sudo add-apt-repository ppa:ua-client/staging -y > /dev/null
lxc exec $name -- sudo apt-get update > /dev/null
lxc exec $name -- sudo apt-get upgrade -y > /dev/null
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Only see a warning when creating the bug report
echo -e "\n* Only a warning in collect-logs"
echo "###########################################"
lxc exec $name -- pro collect-logs
echo -e "###########################################\n"

echo -e "\n* Only a warning in apport-bug"
echo "###########################################"
lxc exec $name -- env APPORT_DISABLE_DISTRO_CHECK=1 ubuntu-bug --save=/tmp/test2 ubuntu-advantage-tools
echo -e "###########################################\n"

cleanup

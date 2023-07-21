#!/bin/bash
set -e

series=$1
token=$2
install_from=$3 # either path to a .deb, or 'staging', or 'proposed'

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
sleep 5

# Install latest ubuntu-advantage-tools
lxc exec $name -- apt-get update > /dev/null
lxc exec $name -- apt-get install  -y ubuntu-advantage-tools > /dev/null
echo -e "\n* Latest u-a-t is installed"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Attach the machine
lxc exec $name -- pro attach $token &> /dev/null
echo -e "\n* Pro is attached, esm-infra is enabled"
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Check esm-infra keys
echo -e "\n* ESM Infra key has trusty in the name"
echo "###########################################"
lxc exec $name -- ls -l /etc/apt/trusted.gpg.d/ | grep esm-infra
echo -e "###########################################\n"

# Upgrade u-a-t to new version
# ----------------------------------------------------------------
if [ $install_from == 'staging' ]; then
  lxc exec $name -- sudo add-apt-repository ppa:ua-client/staging -y > /dev/null
  lxc exec $name -- apt-get update > /dev/null
  lxc exec $name -- apt-get install ubuntu-advantage-tools -y > /dev/null
elif [ $install_from == 'proposed' ]; then
  lxc exec $name -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
  lxc exec $name -- apt-get update > /dev/null
  lxc exec $name -- apt-get install ubuntu-advantage-tools -y > /dev/null
else
  lxc file push $install_from $name/new-ua.deb
  lxc exec $name -- dpkg -i /new-ua.deb > /dev/null
fi
# ----------------------------------------------------------------
echo -e "\n* u-a-t now has the change"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Check esm-infra key again
echo -e "\n* ESM Infra key does not have trusty in the name"
echo "###########################################"
lxc exec $name -- ls -l /etc/apt/trusted.gpg.d/ | grep esm-infra
echo -e "###########################################\n"

# apt does not complain when reading esm sources
echo -e "\n* apt update shows esm-infra sources, and no warnings"
echo "###########################################"
lxc exec $name -- apt update
echo -e "###########################################\n"

cleanup

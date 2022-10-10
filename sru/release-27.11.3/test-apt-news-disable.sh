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
lxc exec $name -- apt-cache policy ubuntu-advantage-tools

# Creating Ubuntu Pro beta message
echo -e "\n* Ubuntu Pro beta message on apt-get upgrade"
echo "###########################################"
lxc exec $name -- sudo pro refresh messages
lxc exec $name -- sudo apt-get upgrade -y
echo -e "###########################################\n"

# Upgrading UA to new version
lxc exec $name --  sudo add-apt-repository ppa:ua-client/staging -y > /dev/null
lxc exec $name -- sudo apt-get update > /dev/null
lxc exec $name -- sudo apt-get upgrade -y > /dev/null
lxc exec $name -- apt-cache policy ubuntu-advantage-tools

# Disabling apt news messages
lxc exec $name -- sudo pro config set apt_news=False

# Show that Ubuntu Pro beta message is no longer on apt-get upgrade
echo -e "\n* Ubuntu Pro beta message not in apt-get upgrade"
echo "###########################################"
lxc exec $name -- sudo pro refresh messages
lxc exec $name -- sudo apt-get upgrade -y
echo -e "###########################################\n"

# Enabling apt news messages
lxc exec $name -- sudo pro config set apt_news=True

# Show that Ubuntu Pro beta message is on the end of apt-get upgrade
echo -e "\n* Ubuntu Pro beta message on the end of apt-get upgrade"
echo "###########################################"
lxc exec $name -- sudo pro refresh messages
lxc exec $name -- sudo apt-get upgrade -y
echo -e "###########################################\n"

cleanup

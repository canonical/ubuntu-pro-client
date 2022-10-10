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

# Creating apt new message
echo -e "\n* Ubuntu Pro message on apt upgrade"
echo "###########################################"
lxc exec $name -- sudo pro refresh messages
lxc exec $name -- sudo apt upgrade -y
echo -e "###########################################\n"

echo -e "\n* Ubuntu Pro message also on apt-get upgrade"
echo "###########################################"
lxc exec $name -- sudo apt-get upgrade -y
echo -e "###########################################\n"

# Upgrading UA to new version
lxc exec $name --  sudo add-apt-repository ppa:ua-client/staging -y > /dev/null
lxc exec $name -- sudo apt-get update > /dev/null
lxc exec $name -- sudo apt-get upgrade -y > /dev/null
echo -e "\n* Upgrading UA to new version"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Show updated apt news message
echo -e "\n* apt news messages instead of Ubuntu Pro advertisement"
echo "###########################################"
lxc exec $name -- sudo pro refresh messages
lxc exec $name -- sudo apt upgrade -y
echo -e "###########################################\n"

echo -e "\n* Apt news message not on apt-get upgrade"
echo "###########################################"
lxc exec $name -- sudo apt-get upgrade -y
echo -e "###########################################\n"

# Disabling apt news messages
lxc exec $name -- sudo pro config set apt_news=False

# Show that apt news message is no longer on apt upgrade
echo -e "\n* Apt news message not in apt upgrade after disabling it"
echo "###########################################"
lxc exec $name -- sudo pro refresh messages
lxc exec $name -- sudo apt upgrade -y
echo -e "###########################################\n"

# Enabling apt news messages
lxc exec $name -- sudo pro config set apt_news=True

# Show apt news message is back
echo -e "\n* apt news messages are back after enabling it"
echo "###########################################"
lxc exec $name -- sudo pro refresh messages
lxc exec $name -- sudo apt upgrade -y
echo -e "###########################################\n"

echo -e "\n* Apt news message still not on apt-get upgrade"
echo "###########################################"
lxc exec $name -- sudo apt-get upgrade -y
echo -e "###########################################\n"

cleanup

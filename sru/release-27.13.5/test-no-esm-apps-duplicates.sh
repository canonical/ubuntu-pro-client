#!/bin/bash
set -e

series=$1
name=$series-dev

version=$2
install_from=$3

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

# Install ubuntu-advantage-tools 27.11.1 (version which inserted files by accident)
lxc exec $name -- wget -O ./ua.deb $(curl https://launchpad.net/ubuntu/$series/amd64/ubuntu-advantage-tools/$version | grep -o "http://launchpadlibrarian.net/.*/ubuntu-advantage-tools_${version}_amd64.deb")
lxc exec $name -- dpkg -i ./ua.deb > /dev/null
echo -e "\n* UA version 27.11.1 is installed"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Install a universe package (ansible)
lxc exec $name -- apt-get update > /dev/null
lxc exec $name -- apt-get install ansible -y > /dev/null
echo -e "\n* Ansible (from universe) is installed"
echo "###########################################"
lxc exec $name -- apt-cache policy ansible
echo -e "###########################################\n"

# Run security-status and see the number of esm-apps updates
echo -e "\n* Updates from esm-apps"
echo "###########################################"
lxc exec $name -- pro security-status
echo -e "###########################################\n"

# Run security-status --esm-apps to check for the updates
echo -e "\n* Updates from esm-apps"
echo "###########################################"
lxc exec $name -- pro security-status --esm-apps
echo -e "###########################################\n"

# Install latest ubuntu-advantage-tools ( < 27.13.4 )
lxc exec $name -- apt-get install ubuntu-advantage-tools -y > /dev/null
echo -e "\n* UA is updated to the latest version"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"
lxc exec $name -- apt-get update > /dev/null

# Run security-status and see the number of esm-apps updates
echo -e "\n* Duplicated updates"
echo "###########################################"
lxc exec $name -- pro security-status
echo -e "###########################################\n"

# Run security-status --esm-apps to check for the updates
echo -e "\n* Duplicated updates"
echo "###########################################"
lxc exec $name -- pro security-status --esm-apps
echo -e "###########################################\n"

# Upgrading UA to new version
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
echo -e "\n* UA now has the fix"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Run security-status and see the number of esm-apps updates
echo -e "\n* Updates are back to normal"
echo "###########################################"
lxc exec $name -- pro security-status
echo -e "###########################################\n"

# Run security-status --esm-apps to check for the updates
echo -e "\n* Updates are back to normal"
echo "###########################################"
lxc exec $name -- pro security-status --esm-apps
echo -e "###########################################\n"

# Check that files don't exist where they shouldn't
echo -e "\n* No unauthenticated apt files"
echo "###########################################"
lxc exec $name -- ls /etc/apt/sources.list.d/ubuntu-esm-apps.list || true
echo -e "###########################################\n"

cleanup

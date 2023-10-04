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

# Attach so we can have some gpg keys in place
lxc exec $name -- pro attach $token
echo -e "\n* Pro is attached"
echo "###########################################"
lxc exec $name -- pro status --wait
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

echo -e "\n* Renaiming keys back to their original name"
echo "###########################################"
lxc exec $name -- mv /etc/apt/trusted.gpg.d/ubuntu-pro-esm-infra.gpg /etc/apt/trusted.gpg.d/ubuntu-advantage-esm-infra-trusty.gpg
lxc exec $name -- mv /etc/apt/trusted.gpg.d/ubuntu-pro-esm-apps.gpg /etc/apt/trusted.gpg.d/ubuntu-advantage-esm-apps.gpg
echo -e "###########################################\n"

echo -e "\n* List gpg keys"
echo "###########################################"
lxc exec $name -- ls /etc/apt/trusted.gpg.d/
echo -e "###########################################\n"

# Modify the postinst script to fail after renaming just one key
lxc exec $name -- sed -i "s/^\s\+SERVICES=.*/error/g" /var/lib/dpkg/info/ubuntu-advantage-tools.postinst
echo -e "\n* Running postinst script again"
echo "###########################################"
lxc exec $name -- dpkg-reconfigure ubuntu-advantage-tools || true
echo -e "###########################################\n"

# Check that only one key got renamed
echo -e "\n* List gpg keys"
echo "###########################################"
lxc exec $name -- ls /etc/apt/trusted.gpg.d/
echo -e "###########################################\n"

# Make sure the services are still enabled
echo -e "\n* Check that services are still enabled"
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Check that apt update is working as expected
echo -e "\n* Check that APT update is working as expected"
echo "###########################################"
lxc exec $name -- apt update
echo -e "###########################################\n"

# Disable service which key was not renamed
echo -e "\n* Disable esm-apps service which gpg key was not renamed"
echo "###########################################"
lxc exec $name -- pro disable esm-apps
lxc exec $name -- pro status
echo -e "###########################################\n"

# Check that the GPG key is still there
echo -e "\n* List gpg keys"
echo "###########################################"
lxc exec $name -- ls /etc/apt/trusted.gpg.d/
echo -e "###########################################\n"

# Enable esm-apps
echo -e "\n* Enable esm-apps and check new gpg key is created"
echo "###########################################"
lxc exec $name -- pro enable esm-apps
lxc exec $name -- pro status
lxc exec $name -- ls /etc/apt/trusted.gpg.d/
echo -e "###########################################\n"

# Check that the new GPG key is there
echo -e "\n* check ubuntu-pro-esm-apps.gpg key now exists"
echo "###########################################"
lxc exec $name -- ls /etc/apt/trusted.gpg.d/
echo -e "###########################################\n"

cleanup

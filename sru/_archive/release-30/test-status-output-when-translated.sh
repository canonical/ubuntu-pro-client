#!/bin/bash
set -e

series=$1
token=$2
install_from=$3 # either path to a .deb, or 'staging', or 'proposed'
translation_deb=$4

name=$series-dev

function cleanup {
  lxc delete $name --force
}

function on_err {
  echo -e "Test Failed"
#  cleanup
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

# Attach with the current ubuntu-advantage-tools package
lxc exec $name -- pro attach $token &> /dev/null
echo -e "\n* Pro is attached, esm-infra is enabled"
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
  lxc file push $translation_deb $name/translation.deb
  lxc exec $name -- dpkg -i /new-ua.deb > /dev/null
  lxc exec $name -- dpkg -i /translation.deb > /dev/null
fi
# ----------------------------------------------------------------
echo -e "\n* u-a-t now has the change"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

echo -e "\n* Check translated status"
echo "###########################################"
lxc exec $name -- sh -c "LANGUAGE=pt_BR.UTF-8 pro status"
echo -e "###########################################\n"

echo -e "\n* Check unstranslated status"
echo "###########################################"
lxc exec $name -- pro status
echo -e "###########################################\n"

echo -e "\n* Check translated simulated status"
echo "###########################################"
lxc exec $name -- sh -c "LANGUAGE=pt_BR.UTF-8 pro status --simulate-with-token $token"
echo -e "###########################################\n"

echo -e "\n* Check unstranslated status"
echo "###########################################"
lxc exec $name -- pro status --simulate-with-token $token
echo -e "###########################################\n"

echo -e "\n* Check unattached translated status"
echo "###########################################"
lxc exec $name -- pro detach --assume-yes
lxc exec $name -- sh -c "LANGUAGE=pt_BR.UTF-8 pro status"
echo -e "###########################################\n"

echo -e "\n* Check unstranslated unattached status"
echo "###########################################"
lxc exec $name -- pro status
echo -e "###########################################\n"

cleanup

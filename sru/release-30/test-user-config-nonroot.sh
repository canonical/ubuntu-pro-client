#!/bin/bash
set -e

series=$1
install_from=$2 # either path to a .deb, or 'staging', or 'proposed'

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

echo -e "\n* Modify metering job"
echo "###########################################"
lxc exec $name -- pro config set metering_timer=2000
lxc exec $name -- pro config show
echo -e "###########################################\n"

echo -e "\n* Show that non-root user cannot see the modification"
echo "###########################################"
lxc exec --user 1000 $name -- pro config show
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

echo -e "\n* Show that non-root user now can see the modification"
echo "###########################################"
lxc exec --user 1000 $name -- pro config show
echo -e "###########################################\n"

echo -e "\n* notice that user-config is now world-readable"
echo "###########################################"
lxc exec $name -- ls -la /var/lib/ubuntu-advantage/user-config.json
echo -e "###########################################\n"

cleanup

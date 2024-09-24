#!/bin/bash
set -e

series=$1
install_from=$2 # 'staging', or 'proposed', or the name of a ppa

name=$series-test

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

# Set up source for installing new version
# ----------------------------------------------------------------
if [ $install_from == 'staging' ]; then
  lxc exec $name -- sudo add-apt-repository ppa:ua-client/staging -y > /dev/null
  lxc exec $name -- apt-get update > /dev/null
elif [ $install_from == 'proposed' ]; then
  lxc exec $name -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
  lxc exec $name -- apt-get update
  lxc exec $name -- sh -c "cat > /etc/apt/preferences.d/pro-posed << EOF
Package: ubuntu-advantage-tools ubuntu-pro-client ubuntu-pro-auto-attach ubuntu-advantage-pro ubuntu-pro-client-l10n
Pin: release a=$series-proposed
Pin-Priority: 600
EOF"
else
  lxc exec $name -- sudo add-apt-repository $install_from -y > /dev/null
  lxc exec $name -- apt-get update > /dev/null
fi
# ----------------------------------------------------------------

echo -e "\n* Latest u-a-t is installed from -updates and -proposed enabled with new version available"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools ubuntu-pro-client
echo -e "###########################################\n"

echo -e "\n* Attempt to upgrade to ubuntu-pro-client while simultaneously removing ubuntu-advantage-tools without removing ubuntu-minimal"
echo -e "* This should fail"
echo "###########################################"
set -x
lxc exec $name -- apt install ubuntu-pro-client ubuntu-advantage-tools- ubuntu-minimal -y && RC=$? || RC=$?
test $RC -eq 100
set +x
echo -e "###########################################\n"

cleanup

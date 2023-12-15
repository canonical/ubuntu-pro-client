#!/bin/bash
set -e

series=$1
install_from=$2 # 'staging', or 'proposed', or the name of a ppa
version=$3

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
  lxc exec $name -- apt-get update > /dev/null
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

echo -e "\n* Latest u-a-t is installed from -updates and 31.2 is available in -proposed"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools ubuntu-pro-client
echo -e "###########################################\n"

echo -e "\n* attach prior to upgrade"
echo "###########################################"
lxc exec $name -- pro attach $UACLIENT_BEHAVE_CONTRACT_TOKEN
echo -e "###########################################\n"

echo -e "\n* upgrade to rename"
echo "###########################################"
set -x
# uncomment one of these per run
# lxc exec $name -- apt install ubuntu-advantage-tools -y
# lxc exec $name -- apt install ubuntu-pro-client -y
lxc exec $name -- apt install ubuntu-pro-client=$version -y
# lxc exec $name -- apt upgrade -y
# lxc exec $name -- apt dist-upgrade -y
set +x
echo -e "###########################################\n"

echo -e "\n* autoremove just to make sure it doesn't do anything unexpected"
echo "###########################################"
set -x
lxc exec $name -- apt autoremove -y
set +x
echo -e "###########################################\n"

echo -e "\n* still attached"
echo "###########################################"
lxc exec $name -- pro status
echo -e "###########################################\n"

echo -e "\n* appropriate versions of ubuntu-advantage-tools and ubuntu-pro-client are installed"
echo "###########################################"
lxc exec $name -- apt policy ubuntu-advantage-tools ubuntu-pro-client
echo -e "###########################################\n"

echo -e "\n* dpkg doesn't show obsolete conffiles for ubuntu-advantage-tools"
echo "###########################################"
lxc exec $name -- dpkg-query --showformat='${Conffiles}\n' --show ubuntu-advantage-tools
echo -e "###########################################\n"

if [ "$series" != "xenial" ] && [ "$series" != "bionic" ]; then
  echo -e "\n* reinstall just to make sure it doesn't do anything unexpected"
  echo "###########################################"
  set -x
  lxc exec $name -- apt reinstall ubuntu-advantage-tools
  lxc exec $name -- apt reinstall ubuntu-pro-client
  set +x
  echo -e "###########################################\n"

  echo -e "\n* still attached"
  echo "###########################################"
  lxc exec $name -- pro status
  echo -e "###########################################\n"

  echo -e "\n* appropriate versions of ubuntu-advantage-tools and ubuntu-pro-client are installed"
  echo "###########################################"
  lxc exec $name -- apt policy ubuntu-advantage-tools ubuntu-pro-client
  echo -e "###########################################\n"
fi

cleanup

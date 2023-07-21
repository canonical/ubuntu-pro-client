#!/bin/bash
set -e

series=$1
token=$2
service_to_test=$3 # either fips or fips-updates
install_from=$4 # either path to a .deb, or 'staging', or 'proposed'

name=$series-dev-$service_to_test

function cleanup {
  lxc delete $name --force
}

function on_err {
  echo -e "Test Failed"
  cleanup
  exit 1
}
trap on_err ERR

function check_fips_pin {
    service=$1
    pin=$2
    apt_policy=$(lxc exec $name -- apt-cache policy)
    if grep -q "$pin https://esm.ubuntu.com/$service/ubuntu $series" <<< "$apt_policy"; then
        echo "SUCCESS: $service is pinned to $pin"
    else
        echo "ERROR: $service is pinned to a different value than $pin"
    fi
}

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
echo -e "\n* Pro is attached"
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Enable FIPS
lxc exec $name -- pro enable $service_to_test --assume-yes &> /dev/null
echo -e "\n* FIPS is enabled"
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Verify that FIPS is pinned to 1001
echo -e "\n* Check FIPS pins"
echo "###########################################"
check_fips_pin "$service_to_test" 1001
echo -e "###########################################\n"

# Check the contents of the preferences dir
echo -e "\n* APT preferences directory content"
echo "###########################################"
lxc exec $name -- ls -l /etc/apt/preferences.d/
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

# Check FIPS pins again
echo -e "\n* Check esm pins after upgrading the package"
echo "###########################################"
check_fips_pin "$service_to_test" 1001
echo -e "###########################################\n"

# Check the contents of the preferences dir again
echo -e "\n* APT preferences directory content"
echo "###########################################"
lxc exec $name -- ls -l /etc/apt/preferences.d/
echo -e "###########################################\n"

cleanup

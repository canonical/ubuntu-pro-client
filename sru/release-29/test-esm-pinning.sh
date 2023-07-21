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

function check_esm_pin {
    service=$1
    pin=$2
    apt_policy=$(lxc exec $name -- apt-cache policy)
    if grep -q "$pin https://esm.ubuntu.com/$service/ubuntu $series-$service-updates" <<< "$apt_policy"; then
        echo "SUCCESS: esm-$service is pinned to $pin"
    else
        echo "ERROR: esm-$service is pinned to a different value than $pin"
    fi
}

function disable_esm_services {
    # Disable esm-apps and esm-infra
    # ----------------------------------------------------------------
    echo -e "\n* Disabling esm-infra and esm-apps"
    lxc exec $name -- sudo pro disable esm-infra esm-apps --assume-yes
    echo "###########################################"
    lxc exec $name -- pro status --wait
    echo -e "###########################################\n"
    apt_policy=$(lxc exec $name -- apt-cache policy)
    if grep -q "510 https://esm.ubuntu.com/infra/ubuntu $series-infra-updates" <<< "$apt_policy"; then
        echo "ERROR: esm-infra is still enabled"
    else
        echo "SUCCESS: esm-infra not enabled"
    fi

    if grep -q "510 https://esm.ubuntu.com/apps/ubuntu $series-apps-updates" <<< "$apt_policy"; then
        echo "ERROR: esm-apps is still enabled"
    else
        echo "SUCCESS: esm-apps not enabled"
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
echo -e "\n* Pro is attached, esm-infra is enabled"
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Verify that esm-apps and esm-infra are not pinned
echo -e "\n* Check esm pins"
echo "###########################################"
check_esm_pin "infra" 500
check_esm_pin "apps" 500
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

# Check esm-pins again
echo -e "\n* Check esm pins after upgrading the package"
echo "###########################################"
check_esm_pin "infra" 510
check_esm_pin "apps" 510
echo -e "###########################################\n"

# Disable esm-apps and esm-infra
# ----------------------------------------------------------------
disable_esm_services

# enable esm-apps and esm-infra
# ----------------------------------------------------------------
echo -e "\n* Enabling esm-infra and esm-apps"
lxc exec $name -- sudo pro enable esm-infra esm-apps --assume-yes
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Check esm-pins again
echo -e "\n* Check esm pins after enable"
echo "###########################################"
check_esm_pin "infra" 510
check_esm_pin "apps" 510
echo -e "###########################################\n"

# Disable esm-apps and esm-infra
# ----------------------------------------------------------------
echo -e "\n* Disabling esm-infra and esm-apps"
disable_esm_services
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"


echo -e "\n* Create custom pin files with alphabetical name lower than the Pro pin file"
lxc exec $name -- sudo sh -c 'echo "Package: *\nPin: release o=UbuntuESM\nPin-Priority: 450" > /etc/apt/preferences.d/custom-esm-infra'
lxc exec $name -- sudo sh -c 'echo "Package: *\nPin: release o=UbuntuESMApps\nPin-Priority: 450" > /etc/apt/preferences.d/custom-esm-apps'
echo -e "\n* Enabling esm-infra and esm-apps"
lxc exec $name -- sudo pro enable esm-infra esm-apps --assume-yes
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Check esm-pins again
echo -e "\n* Check esm pins after enable"
echo "###########################################"
check_esm_pin "infra" 450
check_esm_pin "apps" 450
echo -e "###########################################\n"

#  Disable esm-apps and esm-infra
# ----------------------------------------------------------------
echo -e "\n* Disabling esm-infra and esm-apps"
disable_esm_services
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

echo -e "\n* Create custom pin files with alphabetical name higher than the Pro pin file"
lxc exec $name -- sudo rm /etc/apt/preferences.d/custom-esm-infra
lxc exec $name -- sudo rm /etc/apt/preferences.d/custom-esm-apps
lxc exec $name -- sudo sh -c 'echo "Package: *\nPin: release o=UbuntuESM\nPin-Priority: 450" > /etc/apt/preferences.d/zcustom-esm-infra'
lxc exec $name -- sudo sh -c 'echo "Package: *\nPin: release o=UbuntuESMApps\nPin-Priority: 450" > /etc/apt/preferences.d/zcustom-esm-apps'
echo -e "\n* Enabling esm-infra and esm-apps"
lxc exec $name -- sudo pro enable esm-infra esm-apps --assume-yes
echo "###########################################"
lxc exec $name -- pro status --wait
echo -e "###########################################\n"

# Check esm-pins again
echo -e "\n* Check esm pins after enable"
echo "###########################################"
check_esm_pin "infra" 510
check_esm_pin "apps" 510
echo -e "###########################################\n"

cleanup

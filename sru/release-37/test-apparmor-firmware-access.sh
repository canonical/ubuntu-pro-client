#!/bin/bash
set -e

series=$1
install_from=$2  # either path to a .deb, or 'staging', or 'proposed'

name=$series-apparmor-test

function cleanup {
  lxc delete $name --force
}

function on_err {
  echo -e "\nTest FAILED"
  cleanup
  exit 1
}
trap on_err ERR

lxc launch ubuntu-daily:$series $name -c security.nesting=true -c security.privileged=true
sleep 5

# Install latest ubuntu-advantage-tools
lxc exec $name -- apt-get update > /dev/null
lxc exec $name -- apt-get install -y ubuntu-advantage-tools > /dev/null
echo -e "\n* Current ubuntu-advantage-tools installed"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo "###########################################\n"

APPARMOR_PROFILE=/etc/apparmor.d/ubuntu_pro_esm_cache

# ----------------------------------------------------------------
if [ "$install_from" == 'staging' ]; then
  lxc exec $name -- add-apt-repository ppa:ua-client/staging -y > /dev/null
  lxc exec $name -- apt-get update > /dev/null
  lxc exec $name -- apt-get install ubuntu-advantage-tools -y > /dev/null
elif [ "$install_from" == 'proposed' ]; then
  lxc exec $name -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
  lxc exec $name -- apt-get update > /dev/null
  lxc exec $name -- apt-get install ubuntu-advantage-tools -y > /dev/null
else
  lxc file push $install_from $name/new-ua.deb
  lxc exec $name -- dpkg -i /new-ua.deb > /dev/null
fi
# ----------------------------------------------------------------

echo "Setting up hardware mocks to trigger AppArmor..."
lxc exec $name -- bash -c "
  rm -f /var/lib/ubuntu-advantage/status.json
  mount -t tmpfs tmpfs /sys/firmware
  mkdir -p /sys/firmware/devicetree/base/
  mkdir -p /sys/firmware/dmi/entries/0-0/
  echo 'Mock Model' > /sys/firmware/devicetree/base/model
  echo 'Mock DMI' > /sys/firmware/dmi/entries/0-0/raw
"

echo "=== Ensuring AppArmor profile is loaded ==="
lxc exec $name -- apparmor_parser -r $APPARMOR_PROFILE

echo "=== Verifying Devicetree path (main profile) ==="
# If this fails, set -e triggers on_err
lxc exec $name -- aa-exec -p ubuntu_pro_esm_cache python3 -c "open('/sys/firmware/devicetree/base/model').read()"

echo "=== Verifying DMI path (systemd-detect-virt profile) ==="
# We swap cat in to test the path within the restricted profile context
lxc exec $name -- mv /usr/bin/systemd-detect-virt /usr/bin/systemd-detect-virt.bak
lxc exec $name -- cp /usr/bin/cat /usr/bin/systemd-detect-virt

# If aa-exec returns 1 (denied), the script stops here and calls on_err
lxc exec $name -- aa-exec -p ubuntu_pro_esm_cache_systemd_detect_virt systemd-detect-virt /sys/firmware/dmi/entries/0-0/raw > /dev/null

# Clean up the swap (optional since cleanup deletes the LXC, but good practice)
lxc exec $name -- mv /usr/bin/systemd-detect-virt.bak /usr/bin/systemd-detect-virt

echo -e "\n=== Test PASSED ==="

cleanup

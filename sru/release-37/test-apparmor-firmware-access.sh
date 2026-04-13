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
echo -e "###########################################\n"

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
  # 1. Force the code path
  rm -f /var/lib/ubuntu-advantage/status.json
  
  # 2. Create the writeable canvas
  # We mount a tmpfs over /sys/firmware so we can create directories
  mount -t tmpfs tmpfs /sys/firmware
  
  # 3. Re-create the hardware structure
  mkdir -p /sys/firmware/devicetree/base/
  mkdir -p /sys/firmware/dmi/entries/0-0/
  
  # 4. Create the dummy hardware ID files
  echo 'Mock Model' > /sys/firmware/devicetree/base/model
  echo 'Mock DMI' > /sys/firmware/dmi/entries/0-0/raw
"

# --- Run the esm-cache service and check for AppArmor denials ---
echo ""
echo "=== Running esm-cache service under the AppArmor profile ==="

# Ensure apparmor is enforcing the profile
lxc exec $name -- apparmor_parser -r $APPARMOR_PROFILE || true

# Clear the journal log so we only inspect fresh messages
lxc exec $name -- journalctl --rotate > /dev/null 2>&1 || true
lxc exec $name -- journalctl --vacuum-time=1s > /dev/null 2>&1 || true

lxc exec $name -- systemctl start esm-cache.service || true
sleep 3

# --- Verification ---
echo "=== Testing AppArmor Policy Enforcement ==="

# 1. Check Devicetree path under the main profile
echo "Testing: ubuntu_pro_esm_cache -> /sys/firmware/devicetree/base/model"
if ! lxc exec $name -- aa-exec -p ubuntu_pro_esm_cache python3 -c "open('/sys/firmware/devicetree/base/model').read()" > /dev/null 2>&1; then
  echo "FAILED: AppArmor profile DENIED access to the devicetree path."
  cleanup
  exit 1
fi

# 2. Check DMI path under the systemd-detect-virt transition profile
echo "Testing: ubuntu_pro_esm_cache_systemd_detect_virt -> /sys/firmware/dmi/entries/0-0/raw"
if ! lxc exec $name -- aa-exec -p ubuntu_pro_esm_cache_systemd_detect_virt python3 -c "open('/sys/firmware/dmi/entries/0-0/raw').read()" > /dev/null 2>&1; then
  echo "FAILED: AppArmor profile DENIED access to the DMI path."
  cleanup
  exit 1
fi

echo "------------------------------------------------------------"
echo "PASSED: All firmware paths are accessible under correct profiles."
echo "------------------------------------------------------------"

cleanup

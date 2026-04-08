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
echo "Attempting to read firmware paths under profile: $APPARMOR_PROFILE"

# Check both the Device Tree and DMI paths mocked earlier
PATHS_TO_TEST="/sys/firmware/devicetree/base/model /sys/firmware/dmi/entries/0-0/raw"

if lxc exec $name -- aa-exec -p ubuntu_pro_esm_cache python3 -c "
import sys
paths = '$PATHS_TO_TEST'.split()
for p in paths:
    try:
        open(p).read()
        print(f'SUCCESS: Read {p}')
    except Exception as e:
        print(f'FAILURE: Could not read {p} - {e}')
        sys.exit(1)
" ; then
  echo "------------------------------------------------------------"
  echo "PASSED: AppArmor profile ALLOWED access to all firmware paths."
  echo "------------------------------------------------------------"
  cleanup
  exit 0
else
  echo "------------------------------------------------------------"
  echo "FAILED: AppArmor profile DENIED access to one or more paths."
  echo "------------------------------------------------------------"
  cleanup
  exit 1
fi

cleanup

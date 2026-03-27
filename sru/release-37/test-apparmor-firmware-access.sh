#!/bin/bash
# SRU test for LP: #2131292
# Fix: AppArmor denied audit messages when devicetree exists
#
# The ubuntu_pro_esm_cache AppArmor profile previously used the glob rule:
#   /sys/firmware/dmi/entries/** r,
# which generated denial audit messages on systems where /sys/firmware/devicetree
# exists (ARM systems). The fix hard-codes the exact path that systemd-detect-virt
# accesses:
#   /sys/firmware/dmi/entries/0-0/raw r,
#
# Usage: ./test-apparmor-firmware-access.sh <series> <install_from>
#   series:       Ubuntu series name (e.g. jammy, noble)
#   install_from: path to a .deb file, 'staging', or 'proposed'

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


lxc launch ubuntu-daily:$series $name
sleep 5

# Install current ubuntu-advantage-tools
lxc exec $name -- apt-get update > /dev/null
lxc exec $name -- apt-get install -y ubuntu-advantage-tools > /dev/null
echo -e "\n* Current ubuntu-advantage-tools installed"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

APPARMOR_PROFILE=/etc/apparmor.d/ubuntu_pro_esm_cache

# --- Verify the pre-fix state ---
echo "=== Checking AppArmor profile BEFORE fix ==="
lxc exec $name -- grep "sys/firmware" $APPARMOR_PROFILE

OLD_GLOB=$(lxc exec $name -- grep -c "sys/firmware/dmi/entries/\*\*" $APPARMOR_PROFILE || true)
if [ "$OLD_GLOB" -gt 0 ]; then
  echo "PASS: Pre-fix glob rule '/sys/firmware/dmi/entries/**' is present"
else
  echo "INFO: Old glob rule not found - this package may already include the fix"
fi

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

echo ""
echo "=== Checking AppArmor profile AFTER fix ==="
lxc exec $name -- grep "sys/firmware" $APPARMOR_PROFILE

# Verify the fixed rule is present (specific hard-coded path, not glob)
lxc exec $name -- grep -q "sys/firmware/dmi/entries/0-0/raw" $APPARMOR_PROFILE
echo "PASS: Fixed rule '/sys/firmware/dmi/entries/0-0/raw r,' is present"

# Verify the old glob rule is gone
NEW_GLOB=$(lxc exec $name -- grep -c "sys/firmware/dmi/entries/\*\*" $APPARMOR_PROFILE || true)
if [ "$NEW_GLOB" -eq 0 ]; then
  echo "PASS: Old glob rule '/sys/firmware/dmi/entries/**' has been removed"
else
  echo "FAIL: Old glob rule '/sys/firmware/dmi/entries/**' is still present"
  exit 1
fi

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

echo "Checking journal for AppArmor denials from ubuntu_pro_esm_cache..."
DENIALS=$(lxc exec $name -- sh -c "journalctl -b --no-pager 2>/dev/null | grep -c 'apparmor.*DENIED.*ubuntu_pro_esm_cache'" | awk '{print $1}' || echo "0")

if [ "$DENIALS" -eq 0 ]; then
  echo "PASS: No AppArmor denials for ubuntu_pro_esm_cache"
else
  echo "AppArmor denial messages found:"
  lxc exec $name -- sh -c "journalctl -b --no-pager 2>/dev/null | grep 'apparmor.*DENIED.*ubuntu_pro_esm_cache'" || true
  echo "FAIL: $DENIALS AppArmor denial(s) detected after applying the fix"
  exit 1
fi

echo ""
echo "=== All tests passed ==="
cleanup
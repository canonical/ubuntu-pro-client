#!/bin/sh

# Test if upgrading from trusty machine already attached to xenial will keep
# services still enabled after the do-release-upgrade operation. Currently,
# this will not happen because the latest version of uaclient in trusty does
# not enable do-release-upgrade to run a post script that handles the services
# migration when performing an upgrade.
# This script is adding a solution for that problem by manually adding the necessary
# configs for do-release-upgrade (This configurations are done for release 26 forward)
set -x

series=trusty
name=$series-upgrade-lxd

function fix_upgrade_for_esm_infra() {
    # This fix is better documented here:
    # https://github.com/canonical/ubuntu-advantage-client/issues/1590
    multipass exec $name -- sh -c "echo 'Pockets=security,updates,proposed,backports,infra-security,infra-updates,apps-security,apps-updates' >> allow.cfg"
    multipass exec $name -- sh -c "echo '[Distro]\nPostInstallScripts=./xorg_fix_proprietary.py, /usr/lib/ubuntu-advantage/upgrade_lts_contract.py' >> allow.cfg"
}


multipass delete $name
multipass purge
multipass launch $series --name $name

multipass exec $name -- sudo apt-get upgrade -y
multipass exec $name -- sudo apt-get dist-upgrade -y
multipass exec $name -- ua version
multipass exec $name -- sudo ua attach $UACLIENT_BEHAVE_CONTRACT_TOKEN
multipass exec $name -- sudo ua status
multipass exec $name -- sudo sh -c "cat <<EOF >/etc/apt/sources.list.d/ubuntu-$series-proposed.list
deb http://archive.ubuntu.com/ubuntu/ $series-proposed restricted main multiverse universe"
multipass exec $name -- sudo apt-get update
multipass exec $name -- sudo mkdir -p /etc/update-manager/release-upgrades.d  
multipass exec $name -- sh -c "echo '[Sources]\nAllowThirdParty=yes' > allow.cfg"

fix_upgrade_for_esm_infra

multipass exec $name -- sudo mv allow.cfg /etc/update-manager/release-upgrades.d   
multipass exec $name -- sudo do-release-upgrade --frontend DistUpgradeViewNonInteractive
multipass exec $name -- sudo ua status
multipass exec $name -- sudo reboot

multipass exec $name -- sudo reboot
sleep 60
multipass exec $name -- sudo ua status --wait

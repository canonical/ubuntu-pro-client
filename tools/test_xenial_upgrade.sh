#!/usr/bin/bash

set -x
set -e
name=test-xenial-ua-upgrade

function h1() {
    set +x
    echo ""
    echo ""
    echo ""
    echo "############################################################################"
    echo "## $1"
    echo "############################################################################"
    echo ""
    set -x
}
function h2() {
    set +x
    echo ""
    echo ""
    echo "-> $1"
    echo "----------------------------------------------------------------------------"
    echo ""
    set -x
}


function setup() {
    tool=$1

    h2 "Make sure we're up to date"
    $tool exec $name -- sudo apt update
    $tool exec $name -- sudo apt upgrade -y
    $tool exec $name -- sudo apt install ubuntu-advantage-tools -y

    h2 "Initial State"
    $tool exec $name -- apt-cache policy ubuntu-advantage-tools
    $tool exec $name -- sudo ubuntu-advantage status
    $tool exec $name -- dpkg-query -L ubuntu-advantage-tools
}
function setup_container() {
    h1 "Setting up fresh container"
    lxc delete --force $name || true
    lxc launch ubuntu-daily:xenial $name
    sleep 10

    setup lxc
}
function setup_vm() {
    h1 "Setting up fresh vm"
    multipass delete -p $name || true
    multipass launch -n $name xenial
    sleep 10

    setup multipass
}
function teardown_container() {
    lxc delete --force $name || true
}
function teardown_vm() {
    multipass delete -p $name || true
}

function install_new_ua() {
    tool=$1
    h2 "Set up to use daily ppa"
    $tool exec $name -- sudo add-apt-repository ppa:ua-client/daily -y
    $tool exec $name -- sudo apt update

    h2 "Actually install - verify there are no errors"
    $tool exec $name -- sudo apt install ubuntu-advantage-tools -y
}

function attach_ua() {
    tool=$1
    set +x
    echo "+ $tool exec $name -- sudo ua attach \$UACLIENT_BEHAVE_CONTRACT_TOKEN"
    $tool exec $name -- sudo ua attach $UACLIENT_BEHAVE_CONTRACT_TOKEN
    set -x
}




function test_upgrade_in_container() {
    setup_container

    h1 "Upgrade to UA 27 while unattached"

    install_new_ua lxc

    h2 "Check for leftover files from old version - verify nothing unexpected is left behind"
    lxc exec $name -- ls -l /etc/update-motd.d/99-esm /usr/share/keyrings/ubuntu-esm-keyring.gpg /usr/share/keyrings/ubuntu-fips-keyring.gpg /usr/share/man/man1/ubuntu-advantage.1.gz /usr/share/doc/ubuntu-advantage-tools/copyright /usr/share/doc/ubuntu-advantage-tools/changelog.gz /usr/bin/ubuntu-advantage || true

    h2 "New Status - verify esm-infra available but not enabled; esm-apps not visible"
    lxc exec $name -- ua status

    h2 "Attach - verify esm-infra automatically enabled; esm-apps not visible"
    attach_ua lxc

    h2 "Detaching before destruction"
    lxc exec $name -- ua detach --assume-yes

    teardown_container
}


function test_upgrade_with_livepatch_in_vm() {

    setup_vm

    h1 "Upgrade to UA 27 while old version has livepatch enabled"

    h2 "Enable livepatch on old version"
    set +x
    echo "+ multipass exec $name -- ubuntu-advantage enable-livepatch \$LIVEPATCH_TOKEN"
    multipass exec $name -- sudo ubuntu-advantage enable-livepatch $LIVEPATCH_TOKEN
    set -x

    h2 "Status before - old UA and livepatch say enabled"
    multipass exec $name -- sudo canonical-livepatch status
    multipass exec $name -- sudo ubuntu-advantage status

    install_new_ua multipass

    h2 "Status after upgrade - livepatch still enabled but new UA doesn't report it"
    multipass exec $name -- sudo canonical-livepatch status
    multipass exec $name -- sudo ua status

    h2 "Attach - verify that livepatch is disabled and re-enabled"
    attach_ua multipass

    h2 "Status after attach - both livepatch and UA should say enabled"
    multipass exec $name -- sudo canonical-livepatch status
    multipass exec $name -- sudo ua status

    h2 "Detaching before destruction"
    multipass exec $name -- sudo ua detach --assume-yes

    teardown_vm
}

function test_upgrade_with_fips_in_vm() {

    setup_vm

    h1 "Upgrade to UA 27 while old version has fips enabled"

    h2 "Manual fips check says disabled (file doesn't exist)"
    multipass exec $name -- sudo cat /proc/sys/crypto/fips_enabled || true

    h2 "Enable fips on old version"
    set +x
    echo "+ multipass exec $name -- ubuntu-advantage enable-fips \$FIPS_CREDS"
    multipass exec $name -- sudo ubuntu-advantage enable-fips $FIPS_CREDS
    set -x

    h2 "Reboot to finish fips activation"
    multipass exec $name -- sudo reboot || true
    sleep 20

    h2 "Status before upgrade - old UA says fips is enabled, manual check agrees"
    multipass exec $name -- sudo ubuntu-advantage status
    multipass exec $name -- sudo cat /proc/sys/crypto/fips_enabled

    h2 "Source added by old client is present"
    multipass exec $name -- sudo ls /etc/apt/sources.list.d
    multipass exec $name -- sudo grep -o private-ppa.launchpad.net/ubuntu-advantage/fips/ubuntu /etc/apt/sources.list.d/ubuntu-fips-xenial.list

    install_new_ua multipass

    h2 "Status after upgrade - new UA won't say anything is enabled, but a manual check still says fips is enabled"
    multipass exec $name -- sudo ua status
    multipass exec $name -- sudo cat /proc/sys/crypto/fips_enabled

    h2 "Source file added by old client is renamed but contents left unchanged"
    multipass exec $name -- sudo ls /etc/apt/sources.list.d
    multipass exec $name -- sudo grep -o private-ppa.launchpad.net/ubuntu-advantage/fips/ubuntu /etc/apt/sources.list.d/ubuntu-fips.list

    h2 "Attach - only esm-infra will be auto-enabled"
    attach_ua multipass

    h2 "Status after attach - new UA will say fips is disabled, livepatch is n/a, and there is a notice to enable fips"
    multipass exec $name -- sudo ua status
    multipass exec $name -- sudo cat /proc/sys/crypto/fips_enabled

    h2 "Enable fips on new UA - This will re-install fips packages and ask to reboot again"
    multipass exec $name -- sudo ua enable fips --assume-yes


    h2 "Status after enabled but before reboot - UA says fips enabled, notice to enable fips is gone"
    multipass exec $name -- sudo ua status
    multipass exec $name -- sudo cat /proc/sys/crypto/fips_enabled

    h2 "Source added by old client is replaced with new source"
    set +x
    echo "multipass exec $name -- sudo grep \$FIPS_CREDS /etc/apt/sources.list.d/ubuntu-fips.list && echo \"FAIL: found oldclient FIPS creds\" || echo \"SUCCESS: Migrated to new client creds\""
    multipass exec $name -- sudo grep $FIPS_CREDS /etc/apt/sources.list.d/ubuntu-fips.list && echo "FAIL: found oldclient FIPS creds" || echo "SUCCESS: Migrated to new client creds"
    set -x
    multipass exec $name -- sudo ls /etc/apt/sources.list.d
    multipass exec $name -- sudo cat /etc/apt/sources.list.d/ubuntu-fips.list
    multipass exec $name -- sudo apt update

    h2 "Check to make sure we have a valid ubuntu-*-fips metapackage installed"
    multipass exec $name -- sudo grep "install" /var/log/ubuntu-advantage.log

    h2 "Reboot to finish second fips activation"
    multipass exec $name -- sudo reboot || true
    sleep 20

    h2 "Status after reboot - new UA will say fips is enabled, manual check agrees"
    multipass exec $name -- sudo ua status
    multipass exec $name -- sudo cat /proc/sys/crypto/fips_enabled

    h2 "Detaching before destruction"
    multipass exec $name -- sudo ua detach --assume-yes

    teardown_vm
}

test_upgrade_in_container
test_upgrade_with_livepatch_in_vm
test_upgrade_with_fips_in_vm

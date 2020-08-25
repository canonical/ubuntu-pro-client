#!/bin/bash


cat >install-24.3-uat.yaml <<EOF
#cloud-config
ssh_import_id: [lamoura]
apt:                                                                            
  sources:                                                                      
    testingpro:
      source: "ppa:chad.smith/test-ua-client-do-release-upgrade"
      keyid: 78030E2CC630045124EC2CAB83712B78F5B6FD57
packages:                                                                       
  - ubuntu-advantage-tools                                                      
  - ubuntu-advantage-pro    
EOF

while [[ "$#" -gt 0 ]]; do
    case $1 in
        -b|--base-release) BASE_RELEASE="$2"; shift ;;
        -u|--upgrade-release) UPGRADE_RELEASE="$2"; shift;;
        -c|--contract-token) CONTRACT_TOKEN="$2"; shift ;;
    esac
    shift
done

VM_NAME=sru-$BASE_RELEASE
EXPECTED_UA_VERSION="25.1~18.04.1"

function launch_base_vm() {
    echo "##############################"
    echo "Create $BASE_RELEASE container"
    lxc delete --force $VM_NAME
    lxc launch ubuntu-daily:$BASE_RELEASE $VM_NAME -c user.user-data="$(cat install-24.3-uat.yaml)"
    echo "##############################"
}

function wait_for_cloud_init_to_complete(){
    echo "##############################"
    echo "Wait for cloud-init completion"

    cmd="cloud-init status --wait 2&>1 > /dev/null || [[ $(runlevel) = 'N 2' ]] && [ -f /run/cloud-init/result.json ]"

    i=0;
    while [ $i -lt 120 ] && i=$(($i+1))
    do
      lxc exec $VM_NAME -- sh -c "$cmd"
      cmd_output=$(lxc exec $VM_NAME -- echo $?)
      if [ "$cmd_output" = "0" ]; then
          break
      fi

      sleep 1
    done

    if [ ! "$cmd_output" = "0" ]; then
        echo "Failed to run cloud-init"
    fi
}

function check_uaclient_status() {
    echo "##############################"
    echo "Check uaclient status"
    lxc exec $VM_NAME ua version
    lxc exec $VM_NAME ua status
    echo "##############################"
}

function attach_to_uaclient() {
    echo "##############################"
    echo "Attach uaclient to a subscription"
    lxc exec $VM_NAME ua attach $CONTRACT_TOKEN
    echo "##############################"
}

function upgrade_release(){
    echo "##############################"
    echo "do-release-upgrade $BASE_RELEASE -> $UPGRADE_RELEASE"
    echo "Call do-release-upgrade with AllowThirdPart=yes for PPA upgrades"
    lxc exec $VM_NAME -- sudo mkdir -p /etc/update-manager/release-upgrades.d                            
    lxc exec $VM_NAME -- sh -c "echo '[Sources]\nAllowThirdParty=yes' > allow.cfg"
    lxc exec $VM_NAME -- sudo mv allow.cfg /etc/update-manager/release-upgrades.d   
    lxc exec $VM_NAME -- sudo apt update
    lxc exec $VM_NAME -- sudo apt upgrade -y
    lxc exec $VM_NAME -- script /dev/null -c "yes | do-release-upgrade -q -f DistUpgradeViewNonInteractive"
    echo "##############################"
}

function check_if_release_was_upgraded(){
    echo "##############################"
    echo "Checking uaclient version"
    current_release=$(lxc exec $VM_NAME -- lsb_release -c | awk '{print $2}')
    if [ "$current_release" = "$UPGRADE_RELEASE" ]; then
        echo "SUCCESS: release was updated to $UPGRADE_RELEASE"
    else
        echo "FAILURE: failed to update to $UPGRADE_RELEASE"
    fi
    echo "##############################"
}

function check_uaclient_release(){
    echo "##############################"
    echo "Confirm UA version"
    ua_version=$(lxc exec $VM_NAME -- ua version)
    if [ "$ua_version" = "$EXPECTED_UA_VERSION" ]; then
        echo "SUCCESS: uaclient was updated to $ua_version"
    else
        echo "FAILURE: uaclient was not updated to $ua_version"
    fi
    echo "##############################"
}

function check_if_esm_source_was_upgraded(){
    echo "##############################"
    echo "Check esm url reflects $UPGRADE_RELEASE release"
    esm_sources=$(lxc exec $VM_NAME -- apt-cache policy | grep esm)
    echo $esm_sources
    if [[ $esm_sources =~ "$UPGRADE_RELEASE" ]]; then
        echo "SUCCESS: found $UPGRADE_RELEASE in apt-cache policy esm source"
    else
        echo "FAILURE: did not found $UPGRADE_RELEASE in apt-cache policy esm source"
    fi
    echo "##############################"
}

function install_pkg_from_esm(){
    pkgname=$1

    echo "##############################"
    echo "Check if esm package can be installed"
    echo "Confirm $pkgname is installable for $UPGRADE_RELEASE esm PPA"
    lxc exec $VM_NAME -- apt-get install -y $pkgname
    echo "##############################"
}

function get_files_for_inspection(){
    echo "##############################"
    echo "Creating $BASE_RELEASE folder with test results"

    if [ -d "$BASE_RELEASE" ]; then
        rm -rf $BASE_RELEASE
    fi

    lxc exec $VM_NAME -- sh -c "dpkg -l > /tmp/dpkg.list"
    lxc file pull -r $VM_NAME/etc $BASE_RELEASE
    lxc file pull -r $VM_NAME/tmp/dpkg.list $BASE_RELEASE
    lxc file pull -r $VM_NAME/var/lib/ubuntu-advantage $BASE_RELEASE/var/lib
    echo "##############################"
}

echo --- BEGIN test: dist-upgrade an esm-enable $BASE_RELEASE to $UPGRADE_RELEASE
launch_base_vm
wait_for_cloud_init_to_complete
attach_to_uaclient
upgrade_release
check_if_release_was_upgraded
check_uaclient_release

echo "Verifying if uaclient is still attached"
check_uaclient_status
check_if_esm_source_was_upgraded
install_pkg_from_esm libkrad0
get_files_for_inspection
lxc stop $VM_NAME

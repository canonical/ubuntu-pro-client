#!/bin/sh

pro_deb=$1
LOCATION=$2
UBUNTU_IMAGE=$3
INSTANCE_NAME="pro-tat-vm"
RESOURCE_GROUP="proclient-testing-auto-attach"
USER="proclient"

set -e

GREEN="\e[32m"
RED="\e[31m"
BLUE="\e[36m"
END_COLOR="\e[0m"

function cleanup {
    az vm run-command invoke \
        --name $INSTANCE_NAME \
        --resource-group $RESOURCE_GROUP \
        --command-id RunShellScript \
        --scripts "sudo pro detach --assume-yes || true"

    az group delete --name $RESOURCE_GROUP --yes
    az extension remove --name ssh
    rm az_sshconfig

}

function setup {
    az group create \
        --location $LOCATION \
        --name $RESOURCE_GROUP
    az extension add --name ssh --yes
}

function on_err {
    echo -e "${RED}Test Failed${END_COLOR}"
    cleanup
    exit 1
}

trap on_err ERR

function run_cmd {
    az vm run-command invoke \
        --name $INSTANCE_NAME \
        --resource-group $RESOURCE_GROUP \
        --command-id RunShellScript \
        --scripts "sh -c \"$@\""

}

function print_and_run_cmd {
    echo -e "${BLUE}Running:${END_COLOR}" "$@"
    echo -e "${BLUE}Output:${END_COLOR}"
    run_cmd "$@"
    echo
}

function explanatory_message {
    echo -e "${BLUE}$@${END_COLOR}"
}

explanatory_message "Setting up the resource group"
setup
explanatory_message "Starting azure instance"
az vm create \
    --name $INSTANCE_NAME \
    --resource-group $RESOURCE_GROUP \
    --image $UBUNTU_IMAGE \
    --public-ip-sku Standard \
    --admin-username $USER \
    --generate-ssh-keys

az ssh config \
    --resource-group $RESOURCE_GROUP \
    --name $INSTANCE_NAME --file az_sshconfig \
    --local-user $USER

explanatory_message "Installing new version of ubuntu-advantage-tools from local copy"
scp -F ./az_sshconfig $pro_deb $RESOURCE_GROUP-$INSTANCE_NAME-$USER:/tmp/pro-client.deb
run_cmd "sudo apt update"
run_cmd "sudo apt install ubuntu-advantage-tools jq -y"
print_and_run_cmd "sudo dpkg -i /tmp/pro-client.deb"

explanatory_message "Checking the status and logs beforehand"
print_and_run_cmd "sudo pro status --wait"
print_and_run_cmd "sudo cat /var/log/ubuntu-advantage-daemon.log"
print_and_run_cmd "sudo truncate -s 0 /var/log/ubuntu-advantage-daemon.log"

explanatory_message "Updating the license type in the VM IMDS data"
res=$(az vm update \
        --resource-group $RESOURCE_GROUP \
        --name $INSTANCE_NAME \
    --license-type UBUNTU_PRO)

explanatory_message "Biding our time until IMDS updates the licenseType, before auto attaching"
sleep 30
explanatory_message "Now with the license, it will succeed auto_attaching"
print_and_run_cmd "sudo pro auto-attach"
print_and_run_cmd "sudo pro status --wait"
print_and_run_cmd "sudo cat /var/log/ubuntu-advantage-daemon.log"
result=$(run_cmd "sudo pro status --format json")
echo $result | jq '.value[].message' | sed -e 's/\[stderr\]\\n"//g' -e 's/"Enable succeeded: \\n\[stdout]\\n//g' -e 's/\\n//g' -e 's/\\"/\"/g' | jq -r ".attached" | grep "true"

echo -e "${GREEN}Test Passed${END_COLOR}"
cleanup

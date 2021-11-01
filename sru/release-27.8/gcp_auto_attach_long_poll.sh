#!/bin/sh
ua_deb=$1
ZONE="us-east1-b"
INSTANCE_NAME="test-auto-attach"
INSTANCE_TYPE="n1-standard-1"
DISK_NAME="persistent-disk-0"

set -e

GREEN="\e[32m"
RED="\e[31m"
BLUE="\e[36m"
END_COLOR="\e[0m"

function cleanup {
  gcloud compute ssh $INSTANCE_NAME -- "sudo ua detach --assume-yes || true"
  gcloud compute instances delete $INSTANCE_NAME
}

function on_err {
  echo -e "${RED}Test Failed${END_COLOR}"
  cleanup
  exit 1
}

trap on_err ERR

function print_and_run_cmd {
    echo -e "${BLUE}Running:${END_COLOR}" "$@"
    echo -e "${BLUE}Output:${END_COLOR}"
    gcloud compute ssh $INSTANCE_NAME -- "sh -c \"$@\""
    echo
}

function explanatory_message {
    echo -e "${BLUE}$@${END_COLOR}"
}

explanatory_message "Starting gcloud instance"
gcloud compute instances create $INSTANCE_NAME \
    --image="ubuntu-2004-focal-v20220204" \
    --image-project="ubuntu-os-cloud" \
    --machine-type=$INSTANCE_TYPE \
    --zone=$ZONE
sleep 60

explanatory_message "Installing new version of ubuntu-advantage-tools from local copy"
gcloud compute scp $ua_deb $INSTANCE_NAME:/tmp/ubuntu-advantage-tools.deb
gcloud compute ssh $INSTANCE_NAME -- "sudo apt update"
gcloud compute ssh $INSTANCE_NAME -- "sudo apt install ubuntu-advantage-tools -y"
print_and_run_cmd "sudo dpkg -i /tmp/ubuntu-advantage-tools.deb"

explanatory_message "skip initial license check"
print_and_run_cmd "sudo sed -zi \\\"s/cloud.is_pro_license_present(\n            wait_for_change=False\n        )/False/\\\" /usr/lib/python3/dist-packages/uaclient/daemon.py"

explanatory_message "turn on polling in config file"
print_and_run_cmd "sudo sh -c \\\"printf \\\\\\\"  poll_for_pro_license: true\\\\\\\" >> /etc/ubuntu-advantage/uaclient.conf\\\""

explanatory_message "change won't happen while daemon is running, so set short timeout to simulate the long poll returning"
print_and_run_cmd "sudo sed -i \\\"s/wait_for_change=true/wait_for_change=true\&timeout_sec=5/\\\" /usr/lib/python3/dist-packages/uaclient/clouds/gcp.py"

explanatory_message "Installing new version of cloud-init with cloud-id file feature and rebooting"
print_and_run_cmd "sudo add-apt-repository ppa:cloud-init-dev/daily -y"
print_and_run_cmd "sudo apt install cloud-init -y"
gcloud compute instances stop $INSTANCE_NAME
gcloud compute instances start $INSTANCE_NAME
sleep 30

explanatory_message "Checking the status and logs beforehand"
print_and_run_cmd "sudo ua status --wait"
print_and_run_cmd "sudo cat /var/log/ubuntu-advantage-daemon.log"
gcloud compute ssh $INSTANCE_NAME -- "sudo truncate -s 0 /var/log/ubuntu-advantage-daemon.log"

explanatory_message "Stopping the machine, adding license, restarting..."
gcloud compute instances stop $INSTANCE_NAME
gcloud beta compute disks update $INSTANCE_NAME --zone=$ZONE --update-user-licenses="https://www.googleapis.com/compute/v1/projects/ubuntu-os-pro-cloud/global/licenses/ubuntu-pro-2004-lts"
gcloud compute instances start $INSTANCE_NAME
sleep 60

explanatory_message "Now with the license, it will succeed auto_attaching"
print_and_run_cmd "sudo ua status --wait"
print_and_run_cmd "sudo cat /var/log/ubuntu-advantage-daemon.log"
result=$(gcloud compute ssh $INSTANCE_NAME -- "sudo ua status --format json")
echo $result | jq -r ".attached" | grep "true"

echo -e "${GREEN}Test Passed${END_COLOR}"
cleanup

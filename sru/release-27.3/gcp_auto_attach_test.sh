#!/bin/sh
ZONE="us-east1-b"
INSTANCE_NAME="test-auto-attach"
INSTANCE_TYPE="n1-standard-1"
DISK_NAME="persistent-disk-0"

set -x

gcloud compute instances create $INSTANCE_NAME \
    --image="ubuntu-minimal-1604-xenial-v20210430" \
    --image-project="ubuntu-os-cloud" \
    --machine-type=$INSTANCE_TYPE \
    --zone=$ZONE
sleep 30

gcloud compute ssh $INSTANCE_NAME -- "sudo apt install software-properties-common -y"
gcloud compute scp ubuntu-advantage-tools.deb $INSTANCE_NAME:/tmp/
gcloud compute ssh $INSTANCE_NAME -- "sudo apt update"
gcloud compute ssh $INSTANCE_NAME -- "sudo apt install ubuntu-advantage-tools -y"
gcloud compute ssh $INSTANCE_NAME -- "sudo dpkg -i /tmp/ubuntu-advantage-tools.deb"
gcloud compute ssh $INSTANCE_NAME -- "sudo sh -c \"printf \\\"    else:\n        print('pro license not present')\\\" >>  /usr/lib/python3/dist-packages/uaclient/jobs/gcp_auto_attach.py\""
# Without the license, it will not try to auto_attach
gcloud compute ssh $INSTANCE_NAME -- "sudo rm /var/lib/ubuntu-advantage/jobs-status.json"
gcloud compute ssh $INSTANCE_NAME -- "sudo python3 /usr/lib/ubuntu-advantage/timer.py"
gcloud compute ssh $INSTANCE_NAME -- "sudo ua status --wait"

gcloud compute instances stop $INSTANCE_NAME
gcloud beta compute disks update $INSTANCE_NAME --zone=$ZONE --update-user-licenses="https://www.googleapis.com/compute/v1/projects/ubuntu-os-pro-cloud/global/licenses/ubuntu-pro-1604-lts"
gcloud compute instances start $INSTANCE_NAME
sleep 30

# Now with the license, it will succeed auto_attaching
gcloud compute ssh $INSTANCE_NAME -- "sudo rm /var/lib/ubuntu-advantage/jobs-status.json"
gcloud compute ssh $INSTANCE_NAME -- "sudo python3 /usr/lib/ubuntu-advantage/timer.py"
gcloud compute ssh $INSTANCE_NAME -- "sudo ua status --wait"
gcloud compute ssh $INSTANCE_NAME -- "sudo ua detach --assume-yes"

gcloud compute instances delete $INSTANCE_NAME

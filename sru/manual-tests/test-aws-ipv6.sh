#!/bin/sh

set -e

KEY_PATH=$1
DEB_PATH=$2
sshopts=( -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR )

REGION=us-west-2
INSTANCE_TYPE=t3.micro
KEY_NAME=KEY_NAME
PRO_IMAGE_ID=ami-07e00b8a1a054fdbf  # bionic PRO image for us-west-2

# You need to have a subnet that supports IPv6. The easiest path here is to launch an ec2
# unstance through pycloudlib, which will already create a VPC with a subnet that supports
# IPv6. You can also use the security group created by pycloudlib
SUBNET_ID=<SUBNET-ID>
SECURITY_GROUP_ID=<SG-ID>

# Make sure that the awscli being used has support for the --metadata-options params, otherwise the
# IPv6 endpoint will not work as expected
instance_info=$(aws --region $REGION ec2 run-instances --instance-type $INSTANCE_TYPE --image-id $PRO_IMAGE_ID --subnet-id $SUBNET_ID --key-name $KEY_NAME --associate-public-ip-address --ipv6-address-count 1 --metadata-options HttpEndpoint=enabled,HttpProtocolIpv6=enabled --security-group-ids $SECURITY_GROUP_ID)
instance_id=$(echo $instance_info | jq -r ".Instances[0].InstanceId")
instance_ip=$(aws ec2 describe-instances --region $REGION --instance-ids $instance_id --query 'Reservations[*].Instances[*].PublicIpAddress' --output text)

echo "---------------------------------------------"
echo "Checking instance info"
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- lsb_release -a
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo ua status --wait
echo "---------------------------------------------"
echo -e "\n"

echo "---------------------------------------------"
echo "Detaching PRO instance"
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo ua detach --assume-yes
echo "---------------------------------------------"
echo -e "\n"

echo "---------------------------------------------"
echo "Installing package with IPv6 support"
scp "${sshopts[@]}" -i $KEY_PATH $DEB_PATH ubuntu@$instance_ip:/home/ubuntu/ua.deb
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo dpkg -i ua.deb
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- ua version
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo ua status --wait
echo "---------------------------------------------"
echo -e "\n"

echo "---------------------------------------------"
echo "Modifying IPv4 address to make it fail"
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo rm /var/log/ubuntu-advantage.log
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo sed -i "s/169.254.169.254/169.254.169.1/g" /usr/lib/python3/dist-packages/uaclient/clouds/aws.py
echo "---------------------------------------------"
echo -e "\n"

echo "---------------------------------------------"
echo "Verify that auto-attach still works and IPv6 route was used instead"
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo ua auto-attach
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo ua status
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo grep -F \"Could not reach AWS IMDS at http://169.254.169.1\" /var/log/ubuntu-advantage.log
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo grep -F \"URL [PUT]: http://169.254.169.1/latest/api/token\" /var/log/ubuntu-advantage.log
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo grep -F \"URL [PUT]: http://[fd00:ec2::254]/latest/api/token\" /var/log/ubuntu-advantage.log
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo grep -F \"URL [PUT] response: http://[fd00:ec2::254]/latest/api/token\" /var/log/ubuntu-advantage.log
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo grep -F \"URL [GET]: http://[fd00:ec2::254]/latest/dynamic/instance-identity/pkcs7\" /var/log/ubuntu-advantage.log
ssh "${sshopts[@]}" -i $KEY_PATH ubuntu@$instance_ip -- sudo grep -F \"URL [GET] response: http://[fd00:ec2::254]/latest/dynamic/instance-identity/pkcs7\" /var/log/ubuntu-advantage.log
echo "---------------------------------------------"
echo -e "\n"

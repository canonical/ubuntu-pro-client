#!/bin/bash
set -e

series=$1
install_from=$2 # either path to a .deb, or 'staging', or 'proposed'

name=$series-dev

function cleanup {
  lxc delete $name --force
}

function on_err {   
  echo -e "Test Failed"
  cleanup
  exit 1
}
trap on_err ERR


lxc launch ubuntu-daily:$series $name
sleep 5

# Install latest ubuntu-advantage-tools
lxc exec $name -- apt-get update > /dev/null
lxc exec $name -- apt-get install  -y ubuntu-advantage-tools > /dev/null
echo -e "\n* Latest u-a-t is installed"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Create user-config.json file with the given content
http_proxy_value="http://someuser:somepassword@example.com:3128"
# Create user-config.json file with the given content
lxc exec $name -- sh -c "echo '{\"http_proxy\": \"$http_proxy_value\"}' > /var/lib/ubuntu-advantage/user-config.json"

# ----------------------------------------------------------------
if [ $install_from == 'staging' ]; then
  lxc exec $name -- sudo add-apt-repository ppa:ua-client/staging -y > /dev/null
  lxc exec $name -- apt-get update > /dev/null
  lxc exec $name -- apt-get install ubuntu-advantage-tools -y > /dev/null
elif [ $install_from == 'proposed' ]; then
  lxc exec $name -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
  lxc exec $name -- apt-get update > /dev/null
  lxc exec $name -- apt-get install ubuntu-advantage-tools -y > /dev/null
else
  lxc file push $install_from $name/new-ua.deb
  lxc exec $name -- dpkg -i /new-ua.deb > /dev/null
fi
# ----------------------------------------------------------------

# Check if user-config.json is moved to the private directory
lxc exec $name -- test -e /var/lib/ubuntu-advantage/private/user-config.json;
private_config_contents=$(lxc exec $name -- cat /var/lib/ubuntu-advantage/private/user-config.json)
private_http_proxy_value=$(echo "$private_config_contents" | jq -r '.http_proxy')
# Check if the contents are the same as the previous contents
if [ "$http_proxy_value" == "$private_http_proxy_value" ]; then
  echo "Contents of private/user-config.json have not changed"
fi
# Check if the file permissions are root
echo "Checking file permissions for private/user-config.json:"
lxc exec $name -- stat -c %A /var/lib/ubuntu-advantage/private/user-config.json | grep -- "-rw-------"

# Check if a new public file is created
lxc exec $name -- test -e /var/lib/ubuntu-advantage/user-config.json;
public_config_contents=$(lxc exec $name -- cat /var/lib/ubuntu-advantage/user-config.json)
public_http_proxy_value=$(echo "$public_config_contents" | jq -r '.http_proxy')
# Check if the public_http_proxy_value is "<REDACTED>"
if [ "$public_http_proxy_value" = "<REDACTED>" ]; then
  echo "public_http_proxy_value is <REDACTED>"
fi
# Check if file permissions are public
echo "Checking file permissions for public/user-config.json:"
lxc exec $name -- stat -c %A /var/lib/ubuntu-advantage/user-config.json | grep -- "-rw-r--r--"

cleanup
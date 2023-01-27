#!/bin/bash
set -e

series=$1
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

# Check ubuntu-advantage-tools version
lxc exec $name -- apt-get update > /dev/null
lxc exec $name -- apt-get install ubuntu-advantage-tools > /dev/null
echo -e "\n* UA is still the old one"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Move python snippet to SUT
lxc file push ./python-apt-snippet.py $name/home/ubuntu/python-apt-snippet.py

# Try to run it, see it fails
echo -e "\n* Failure when trying to run the python snippet"
echo "###########################################"
lxc exec $name --user 1000 -- python3 /home/ubuntu/python-apt-snippet.py
echo -e "###########################################\n"

# Upgrading UA to new version
# ----------------------------------------------------------------
# Uncomment next line for staging
lxc exec $name -- sudo add-apt-repository ppa:ua-client/staging -y > /dev/null
# Uncomment next line for -proposed
# lxc exec $name -- sh -c "echo \"deb http://archive.ubuntu.com/ubuntu $series-proposed main\" | tee /etc/apt/sources.list.d/proposed.list"
# ----------------------------------------------------------------

lxc exec $name -- sudo apt-get update > /dev/null
lxc exec $name -- apt-get install ubuntu-advantage-tools > /dev/null
echo -e "\n* Upgrading UA to new version"
echo "###########################################"
lxc exec $name -- apt-cache policy ubuntu-advantage-tools
echo -e "###########################################\n"

# Try to run it, see it passes
echo -e "\n* Success when trying to run the python snippet"
echo "###########################################"
lxc exec $name --user 1000 -- python3 /home/ubuntu/python-apt-snippet.py
echo -e "###########################################\n"

cleanup

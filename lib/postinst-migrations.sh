#!/bin/sh
#
# Migrations from previous ubuntu-pro-client/ubuntu-advantage-tools versions
#
# These exist in this script separate from the *.postinst scripts because they
# may need to be called from either ubuntu-pro-client.postinst or from
# ubuntu-advantage-tools.postinst, depending on the situation.
#
# Because ubuntu-advantage-tools Depends on ubuntu-pro-client,
# ubuntu-pro-client.postinst will always be executed before
# ubuntu-advantage-tools.postinst.
#
# If the system already has ubuntu-pro-client and is upgrading to a new version
# of ubuntu-pro-client, that means all migrations present in
# ubuntu-advantage-tools.postinst must have already run at the time the system
# upgraded to the renamed ubuntu-pro-client. That means the migrations in this
# file can and should execute as part of ubuntu-pro-client.postinst.
#
# If upgrading from before the rename to the current version (from before
# version 31), then not necessarily all migrations inside of
# ubuntu-advantage-tools.postinst will have already run. Because the migrations
# present in this file may depend on those previous migrations, then this file
# must execute at the end of ubuntu-advantage-tools.postinst.
#
# In practice, this file is executed conditionally in either
# ubuntu-pro-client.postinst or ubuntu-advantage-tools.postinst using version
# checks. If we're upgrading from a version earlier than 31, then this executes
# in ubuntu-advantage-tools.postinst. If we're upgrading from version 31 or
# later, then this executes in ubuntu-pro-client.postinst.
#
#
#
# Migrations should always be version-gated using PREVIOUS_PKG_VER and execute
# in order from oldest to newest.
#
# For example:
#   if dpkg --compare-versions "$PREVIOUS_PKG_VER" lt "33~"; then
#       # do the migrations to version 33
#   fi
#   if dpkg --compare-versions "$PREVIOUS_PKG_VER" lt "34~"; then
#       # do the migrations to version 34
#   fi
#

set -e

PREVIOUS_PKG_VER=$1

if dpkg --compare-versions "$PREVIOUS_PKG_VER" lt "32~"; then
    # When we perform the write operation through
    # UserConfigFile we write the public
    # version of the user-config file with all the
    # sensitive data removed.
    # We also move the user-config.json file to the private
    # directory
    source_file="/var/lib/ubuntu-advantage/user-config.json"
    destination_dir="/var/lib/ubuntu-advantage/private"
    # Check if the source file exists
    if [ -f "$source_file" ]; then
        mkdir -p "$destination_dir"
        # Move the user-config.json file to the private directory
        mv "$source_file" "$destination_dir/user-config.json"

        /usr/bin/python3 -c "
from uaclient.files import UserConfigFileObject
try:
    user_config_file = UserConfigFileObject()
    content = user_config_file.read()
    user_config_file.write(content)
except Exception as e:
    print('Error while creating public user-config file: {}'.format(e))
"
    fi
fi

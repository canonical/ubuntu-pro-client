#!/bin/sh -eux
# Refresh the keyring files that we store in the repo
#
# Takes a single argument, the directory in which the keyrings should be
# (re-)created
#
# This statically captures the keys we expect to put in our keyrings, so that
# we have an easy-to-read way of tracking what we currently have in the repo
#
# N.B. This will rename any existing keyrings with the suffix .old.
tmp_dir=$(mktemp -d -t ci-XXXXXXXXXX)

if [ $# != 1 -o ! -d $1 ]; then
 echo "Usage: $0 <key_directory>"
 exit 1
fi

if [ $(lsb_release -sc) != "trusty" ]; then
    echo "ERROR: must run on trusty to ensure compatibility"
    exit 1
fi

TARGET_DIR="$1"

EAL_KEY_ID_XENIAL="9F912DADD99EE1CC6BFFFF243A186E733F491C46"
ESM_KEY_ID_PRECISE="74AE092F7629ACDF4FB17310B4C2AF7A67C7A026"
ESM_KEY_ID_TRUSTY="56F7650A24C9E9ECF87C4D8D4067E40313CB4B13"
ESM_KEY_ID_XENIAL="3CB3DF682220A643B43065E9B30EDAA63D8F61D0"
ESM_KEY_ID_BIONIC="2926E7D347A1955504000A983121D2531EF59819"
# fips and fips-updates are same key ID
FIPS_KEY_ID_XENIAL="E23341B2A1467EDBF07057D6C1997C40EDE22758"

generate_keyrings() {
    KEYRING_DIR="$1"
    shift
    KEYS="$@"

    # Intentionally unquoted so GPG gets the keys as separate arguments

    for key in $KEYS; do
        case $key in
            $EAL_KEY_ID_XENIAL)
                service_name="cc-eal-xenial";;
            $ESM_KEY_ID_PRECISE)
                service_name="esm-infra-precise";;
            $ESM_KEY_ID_TRUSTY)
                service_name="esm-infra-trusty";;
            $ESM_KEY_ID_XENIAL)
                service_name="esm-infra-xenial";;
            $ESM_KEY_ID_BIONIC)
                service_name="esm-infra-bionic";;
            $FIPS_KEY_ID_XENIAL)
                service_name="fips-xenial";;
            *)
                echo "Unhandled key id provided: " $key
                exit 1;
        esac
        keyring_file="$KEYRING_DIR/ubuntu-advantage-$service_name.gpg"
        if [ -e "$keyring_file" ]; then
            mv "$keyring_file" "$keyring_file.old"
        fi
        gpg \
            --keyring "$keyring_file" \
            --no-default-keyring \
            --homedir $tmp_dir \
            --no-options \
            --keyserver keyserver.ubuntu.com \
            --recv-keys $key
    done
    rm $KEYRING_DIR/*gpg~
}


generate_keyrings $TARGET_DIR $EAL_KEY_ID_XENIAL $ESM_KEY_ID_PRECISE $ESM_KEY_ID_TRUSTY $ESM_KEY_ID_XENIAL $ESM_KEY_ID_BIONIC $FIPS_KEY_ID_XENIAL

rm -rf $tmp_dir

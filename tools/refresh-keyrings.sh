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

# NOTE: If replacing keyrings on services that are intended for trusty, the
# keyrings MUST BE pulled on a trusty machine to ensure compatibility with
# trusty gpg tooling.

tmp_dir=$(mktemp -d -t ci-XXXXXXXXXX)

if [ $# != 1 -o ! -d $1 ]; then
 echo "Usage: $0 <key_directory>"
 exit 1
fi

TARGET_DIR="$1"

EAL_KEY_ID="9F912DADD99EE1CC6BFFFF243A186E733F491C46"
ESM_KEY_ID="56F7650A24C9E9ECF87C4D8D4067E40313CB4B13"
FIPS_KEY_ID="E23341B2A1467EDBF07057D6C1997C40EDE22758"
CIS_KEY_ID="81CF06E53F2C513A"

generate_keyrings() {
    KEYRING_DIR="$1"
    shift
    KEYS="$@"

    # Intentionally unquoted so GPG gets the keys as separate arguments

    for key in $KEYS; do
        case $key in
            $EAL_KEY_ID)
                service_name="cc-eal-xenial";;
            $ESM_KEY_ID)
                service_name="esm-infra-trusty";;
            $FIPS_KEY_ID)
                service_name="fips";;  # Same FIPS key for any series
            $CIS_KEY_ID)
                service_name="cis";;
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


generate_keyrings $TARGET_DIR $EAL_KEY_ID $ESM_KEY_ID $FIPS_KEY_ID $CIS_KEY_ID

rm -rf $tmp_dir

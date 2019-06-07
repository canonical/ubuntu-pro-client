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

generate_keyring() {
    KEYRING_FILE="$1"
    shift
    KEYS="$@"

    # Intentionally unquoted so GPG gets the keys as separate arguments
    if [ -e "$KEYRING_FILE" ]; then
        mv "$KEYRING_FILE" "$KEYRING_FILE.old"
    fi
    gpg \
        --keyring "$KEYRING_FILE" \
        --no-default-keyring \
        --keyserver keyserver.ubuntu.com \
        --recv-keys $KEYS
}

TARGET_DIR="$1"

KEYRING_ESM="ubuntu-esm-v2-keyring.gpg"
KEYRING_FIPS="ubuntu-fips-keyring.gpg"
KEYRING_FIPS_UPDATES="ubuntu-fips-updates-keyring.gpg"
KEYRING_CC="ubuntu-cc-keyring.gpg"

KEYS_ESM="4067E40313CB4B13"
KEYS_FIPS="C1997C40EDE22758"
KEYS_FIPS_UPDATES="C1997C40EDE22758"
KEYS_CC="3A186E733F491C46"

generate_keyring "$TARGET_DIR/$KEYRING_ESM" "$KEYS_ESM"
generate_keyring "$TARGET_DIR/$KEYRING_FIPS" "$KEYS_FIPS"
generate_keyring "$TARGET_DIR/$KEYRING_FIPS_UPDATES" "$KEYS_FIPS_UPDATES"
generate_keyring "$TARGET_DIR/$KEYRING_CC" "$KEYS_CC"

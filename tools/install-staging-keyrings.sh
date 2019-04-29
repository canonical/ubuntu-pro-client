#!/bin/sh -eu
# Pull down the keys used in staging, and install them in the current machine
#
# The intended use here is to push this script on to a system and then run it
# in situ.  As this should never be used in production, to simplify
# implementation this script puts all relevant keys in to a single keyring and
# install that keyring multiple times.
#
# !! WARNING !!
# This will install insecure keys in to the machine on which you run it,
# overwriting known-good keys.  DO NOT RUN IT ON YOUR LAPTOP!

KEY_IDS="B220D065"
TARGET_PATHS="ubuntu-cc-keyring.gpg ubuntu-esm-v2-keyring.gpg ubuntu-fips-keyring.gpg ubuntu-fips-updates-keyring.gpg ubuntu-securitybenchmarks-keyring.gpg"

# Create a temporary directory for keyring generation
TMPDIR="$(mktemp -d)"
echo "Working in $TMPDIR..."
cleanup () {
    echo "Cleaning up $TMPDIR..."
    rm -rf "$TMPDIR"
    echo "Removed $TMPDIR."
}
trap cleanup EXIT

KEYRING_FILE="$TMPDIR/keyring.gpg"

for KEY_ID in $KEY_IDS; do
    gpg \
        --homedir "$TMPDIR" \
        --keyring "$KEYRING_FILE" \
        --no-default-keyring \
        --keyserver keyserver.ubuntu.com \
        --recv-keys "$KEY_ID"
done

for TARGET_PATH in $TARGET_PATHS; do
    FULL_TARGET_PATH="/usr/share/keyrings/$TARGET_PATH"
    if [ -w "$FULL_TARGET_PATH" ]; then
        cp "$KEYRING_FILE" "$FULL_TARGET_PATH"
    else
        echo "!!! Not copying to unwriteable path: $FULL_TARGET_PATH"
    fi
done

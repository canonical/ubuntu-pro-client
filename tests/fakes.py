# Fake for commands invoked by the script.

SNAP_LIVEPATCH_INSTALLED = """#!/bin/sh
if [ "$1" = "list" ]; then
    cat <<EOF
Name                 Version  Rev  Developer  Notes
canonical-livepatch  7        22   canonical  -
EOF
elif [ "$1" = "install" ]; then
    cat <<EOF
snap "canonical-livepatch" is already installed, see "snap refresh --help"
EOF
elif [ "$1" = "remove" ]; then
    echo "canonical-livepatch removed"
fi
exit 0
"""

SNAP_LIVEPATCH_NOT_INSTALLED = """#!/bin/sh
if [ "$1" = "list" ]; then
    cat <<EOF
error: no matching snaps installed
EOF
    exit 1
elif [ "$1" = "install" ]; then
    cat <<EOF
canonical-livepatch 7 from 'canonical' installed
EOF
    exit 0
fi
"""

LIVEPATCH_ENABLED = """#!/bin/sh
if [ "$1" = "status" ]; then
    cat <<EOF
kernel: 4.4.0-87.110-generic
fully-patched: true
version: "27.3"
EOF
elif [ "$1" = "enable" ]; then
    echo -n "2017/08/04 18:03:47 Error executing enable?auth-token="
    echo "deafbeefdeadbeefdeadbeefdeadbeef."
    echo -n "Machine-token already exists! Please use 'disable' to delete "
    echo "existing machine-token."
elif [ "$1" = "disable" ]; then
    echo -n "Successfully disabled device. Removed machine-token: "
    echo "deadbeefdeadbeefdeadbeefdeadbeef"
fi
exit 0
"""

LIVEPATCH_DISABLED = """#!/bin/sh
if [ "$1" = "status" ]; then
    cat <<EOF
Machine is not enabled. Please run 'sudo canonical-livepatch enable' with the
token obtained from https://ubuntu.com/livepatch.
EOF
    exit 1
elif [ "$1" = "enable" ]; then
    echo -n "Successfully enabled device. Using machine-token: "
    echo "deadbeefdeadbeefdeadbeefdeadbeef"
fi
exit 0
"""

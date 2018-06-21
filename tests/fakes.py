"""Fake for commands invoked by the script."""

SNAP_LIVEPATCH_INSTALLED = """
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

SNAP_LIVEPATCH_NOT_INSTALLED = """
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

# the error string is made up
LIVEPATCH_UNKNOWN_ERROR = """
cat <<EOF
2018-06-18 17:46:11 something wicked happened here
EOF
exit 1
"""

# regardless of the command, canonical-livepatch will always exit with
# status 1 and a message like this
LIVEPATCH_UNSUPPORTED_KERNEL = """
cat <<EOF
2018/05/24 18:51:29 cannot use livepatch: your kernel "4.15.0-1010-kvm" \
is not eligible for livepatch updates
EOF
exit 1
"""

LIVEPATCH_ENABLED = """
if [ "$1" = "status" ]; then
    cat <<EOF
client-version: "7.23"
architecture: x86_64
cpu-model: QEMU Virtual CPU version 2.5+
last-check: 2018-01-30T16:50:01.99308582Z
boot-time: 2018-01-30T12:49:32Z
uptime: 4h56m26s
status:
- kernel: 4.4.0-87.110-generic
  running: true
  livepatch:
    checkState: checked
    patchState: applied
    version: "33.2"
    fixes: |-
      * CVE-2015-7837 LP: #1509563
      * CVE-2016-0758 LP: #1581202
  
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

LIVEPATCH_DISABLED = """
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

ESM_DISABLED = """
echo "500 http://archive.ubuntu.com/ubuntu precise/main amd64 Packages"
"""


ESM_ENABLED = """
echo "500 https://esm.ubuntu.com/ubuntu precise/main amd64 Packages"
"""

APT_GET_LOG_WRAPPER = """
log_path=$(dirname "$0")/../
echo -- "$@" >> "${log_path}/apt_get.args"
env >> "${log_path}/apt_get.env"
"""

LIVEPATCH_ENABLED_STATUS = """
cat <<EOF
client-version: "7.23"
status:
- kernel: 4.4.0-87.110-generic
  running: true
  livepatch:
    checkState: {check_state}
    patchState: {patch_state}
"""

LIVEPATCH_CHECKED_UNAPPLIED = LIVEPATCH_ENABLED_STATUS.format(
    check_state='checked', patch_state='unapplied')

LIVEPATCH_CHECKED_APPLIED_WITH_BUG = LIVEPATCH_ENABLED_STATUS.format(
    check_state='checked', patch_state='applied-with-bug')

LIVEPATCH_CHECKED_NOTHING_TO_APPLY = LIVEPATCH_ENABLED_STATUS.format(
    check_state='checked', patch_state='nothing-to-apply')

LIVEPATCH_CHECKED_APPLY_FAILED = LIVEPATCH_ENABLED_STATUS.format(
    check_state='checked', patch_state='apply-failed')

LIVEPATCH_CHECKED_APPLYING = LIVEPATCH_ENABLED_STATUS.format(
    check_state='checked', patch_state='applying')

LIVEPATCH_NEEDS_CHECK = LIVEPATCH_ENABLED_STATUS.format(
    check_state='needs-check', patch_state='does not matter')

LIVEPATCH_CHECK_FAILED = LIVEPATCH_ENABLED_STATUS.format(
    check_state='check-failed', patch_state='does not matter')

STATUS_CACHE_LIVEPATCH_ENABLED = """\
esm: disabled (not available)
fips: disabled (not available)
livepatch: enabled
  client-version: "7.23"
  status:
  - kernel: 4.4.0-87.110-generic
    running: true
    livepatch:
      checkState: {check_state}
      patchState: {patch_state}
"""

STATUS_CACHE_NO_LIVEPATCH = """\
esm: disabled (not available)
fips: disabled (not available)
"""

STATUS_CACHE_LIVEPATCH_ENABLED_NO_CONTENT = """\
esm: disabled (not available)
fips: disabled (not available)
livepatch: enabled
"""

STATUS_CACHE_LIVEPATCH_DISABLED_AVAILABLE = """\
esm: disabled (not available)
fips: disabled (not available)
livepatch: disabled
"""

STATUS_CACHE_LIVEPATCH_DISABLED_UNAVAILABLE = """\
esm: disabled (not available)
fips: disabled (not available)
livepatch: disabled (not available)
"""

STATUS_CACHE_LIVEPATCH_DISABLED_UNSUPPORTED = """\
esm: disabled (not available)
fips: disabled (not available)
livepatch: disabled (unsupported kernel)
"""

STATUS_CACHE_MIXED_CONTENT = """\
esm: enabled
    patchState: should-not-be-here
    checkState: should-not-be-here
livepatch: enabled
    checkState: checked
    patchState: applied
"""

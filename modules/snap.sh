# shellcheck disable=SC2039

# snapd needs a 4.4.x *running* kernel
check_snapd_kernel_support() {
    local v1 v2
    v1=$(echo "$KERNEL_VERSION" | cut -d . -f 1)
    v2=$(echo "$KERNEL_VERSION" | cut -d . -f 2)
    test "$v1" -ge "4" -a "$v2" -ge "4"
}

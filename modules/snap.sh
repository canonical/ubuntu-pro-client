# shellcheck disable=SC2039

check_snapd_kernel_support() {
    declare -a version
    mapfile -t version < <(echo -e "${KERNEL_VERSION//[.-]/\\n}")
    # snapd needs a 4.4.x *running* kernel
    test "${version[0]}" -ge "4" -a "${version[1]}" -ge "4"
}

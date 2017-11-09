# shellcheck disable=SC2039

# check if the CPU flag is available in the system.
check_cpu_flag() {
    grep -q '^flags.*\b'"$1"'\b' "$CPUINFO"
}

# return the version of a POWER CPU
power_cpu_version() {
    sed -r -n '/^cpu\s*:\s*POWER([0-9]+).*/ { s//\1/; p; q }' "$CPUINFO"
}

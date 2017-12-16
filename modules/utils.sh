# shellcheck disable=SC2039

error_msg() {
    echo "$@" >&2
}

check_result() {
    local result output
    result=0
    output=$("$@" 2>&1) || result=$?
    if [ $result -ne 0 ]; then
        echo "ERROR"
        if [ -n "$output" ]; then
            error_msg "$output"
        fi
        exit $result
    else
        echo "OK"
    fi
}

check_user() {
    if [ "$(id -u)" -ne 0 ]; then
        error_msg "This command must be run as root (try using sudo)"
        exit 2
    fi
}

not_supported() {
    local message="$1"

    error_msg "$message is currently not supported."
    exit 1
}

is_supported_series() {
    local supported_series_list="$1"

    local supported
    for supported in $supported_series_list; do
        if [ "$supported" = "$SERIES" ]; then
            return 0
        fi
    done
    return 1
}

is_supported_arch() {
    local supported_archs="$1"

    # if list is empty, any arch is supported
    [ -n "$supported_archs" ] || return 0

    local supported
    for supported in $supported_archs; do
        if [ "$supported" = "$ARCH" ]; then
            return 0
        fi
    done
    return 1
}

check_service_support() {
    local title="$1"
    local supported_series="$2"
    local supported_archs="$3"

    if ! is_supported_arch "$supported_archs"; then
        error_msg "Sorry, but $title is not supported on $ARCH"
        exit 7
    fi
    if ! is_supported_series "$supported_series"; then
        error_msg "Sorry, but $title is not supported on $SERIES"
        exit 4
    fi
}

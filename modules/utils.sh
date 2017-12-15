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

# Whether the current series is among supported ones.
is_supported_series() {
    local s
    for s in $1; do
        if [ "$s" = "$SERIES" ]; then
            return 0
        fi
    done
    return 1
}

check_service_support() {
    local title="$1"
    local supported_series="$2"

    if ! is_supported_series "$supported_series"; then
        error_msg "Sorry, but $title is not supported on $SERIES"
        exit 4
    fi
}

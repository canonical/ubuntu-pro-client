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

name_in_list() {
    local name="$1"
    local list="$2"

    local elem
    for elem in $list; do
        if [ "$elem" = "$name" ]; then
            return 0
        fi
    done
    return 1
}

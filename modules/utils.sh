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

call_if_defined() {
    local command="$1"

    type -t "$command" >/dev/null || return 0
    "$@"
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

expand_var() {
    local var="$1"

    echo "${!var}"
}

uppercase() {
    echo "$@" | tr '[:lower:]' '[:upper:]'
}

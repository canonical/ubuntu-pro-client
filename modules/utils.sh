# shellcheck disable=SC2039

error_msg() {
    echo "$@" >&2
}

error_exit() {
    local code="$1"

    declare -A codes=(
        [invalid_command]=1
        [not_root]=2
        [invalid_token]=3
        [release_not_supported]=4
        [kernel_too_old]=5
        [service_already_enabled]=6
        [arch_not_supported]=7
        [service_already_disabled]=8
    )
    exit "${codes[$code]}"
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
        return $result
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

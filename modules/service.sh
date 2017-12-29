# shellcheck disable=SC2039

check_user() {
    if [ "$(id -u)" -ne 0 ]; then
        error_msg "This command must be run as root (try using sudo)"
        exit 2
    fi
}

service_from_command() {
    local command="$1"

     echo "$command" | sed -n -r \
         's,^is-(.+)-enabled$,\1,p;
          s,^(enable|disable)-(.+)$,\2,p'
}

service_enable() {
    local service="$1"
    local token="$2"

    check_user
    service_check_support "$service"
    _service_check_enabled "$service"
    "${service}_validate_token" "$token" || exit 3
    "${service}_enable" "$token"
}

service_is_enabled() {
    local service="$1"

    "${service}_is_enabled"
}

service_check_support() {
    local service="$1"

    check_series_arch_supported "$service"
    call_if_defined "${service}_check_support"
}

_service_check_enabled() {
    local service="$1"

    local service_upper title
    service_upper=$(uppercase "$service")
    title=$(expand_var "${service_upper}_SERVICE_TITLE")

    if service_is_enabled "$service"; then
        error_msg "$title is already enabled"
        return 1
    fi
}

# shellcheck disable=SC2039

service_from_command() {
    local command="$1"

     echo "$command" | sed -n -r \
         's,^is-(.+)-enabled$,\1,p;
          s,^(enable|disable)-(.+)$,\2,p'
}

service_enable() {
    local service="$1"
    local token="$2"

    _service_check_user
    _service_check_support "$service"
    _service_check_enabled "$service" || exit 6
    "${service}_validate_token" "$token" || exit 3
    "${service}_enable" "$token"
}

service_disable() {
    local service="$1"

    _service_check_user
    _service_check_support "$service"
    _service_check_disabled "$service" || exit 8
    shift 1
   "${service}_disable" "$@"
}

service_is_enabled() {
    local service="$1"

    "${service}_is_enabled"
}

_service_check_user() {
    if [ "$(id -u)" -ne 0 ]; then
        error_msg "This command must be run as root (try using sudo)"
        return 2
    fi
}

_service_check_support() {
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

_service_check_disabled() {
    local service="$1"

    local service_upper title
    service_upper=$(uppercase "$service")
    title=$(expand_var "${service_upper}_SERVICE_TITLE")

    if ! service_is_enabled "$service"; then
        error_msg "$title is not enabled"
        return 1
    fi
}

# shellcheck disable=SC2039

service_from_command() {
    local command="$1"

     echo "$command" | sed -n -r \
         's,^is-(.+)-enabled$,\1,p;
          s,^(enable|disable|install)-(.+)$,\2,p'
}

service_enable() {
    local service="$1"
    local token="$2"

    service_check_user
    service_check_support "$service"
    _service_check_enabled "$service" || error_exit service_already_enabled
    "${service}_validate_token" "$token" || error_exit invalid_token
    "${service}_enable" "$token"
}

service_disable() {
    local service="$1"

    service_check_user
    service_check_support "$service"
    _service_check_disabled "$service" || error_exit service_already_disabled
    shift 1
   "${service}_disable" "$@"
}

service_is_enabled() {
    local service="$1"

    "${service}_is_enabled"
}

service_print_status() {
    local service="$1"

    local series archs
    series=$(expand_var "${service^^}_SUPPORTED_SERIES")
    archs=$(expand_var "${service^^}_SUPPORTED_ARCHS")

    local status=""
    if "${service}_is_enabled"; then
        status="enabled"
    else
        status="disabled"
        if ! is_supported "$series" "$archs"; then
            status+=" (not available)"
        else
            status+=$(service_disabled_reason "${service}")
        fi
    fi

    echo "$service: $status"
    if [ "$status" = enabled ]; then
        _service_print_detailed_status "$service"
    fi
}

service_disabled_reason() {
    local service="$1"

    call_if_defined "${service}_disabled_reason"
}

service_check_user() {
    if [ "$(id -u)" -ne 0 ]; then
        error_msg "This command must be run as root (try using sudo)"
        error_exit not_root
    fi
}

service_check_support() {
    local service="$1"

    check_series_arch_supported "$service"
    call_if_defined "${service}_check_support"
}

_service_check_enabled() {
    local service="$1"

    local title
    title=$(expand_var "${service^^}_SERVICE_TITLE")
    if service_is_enabled "$service"; then
        error_msg "$title is already enabled"
        return 1
    fi
}

_service_check_disabled() {
    local service="$1"

    local title
    title=$(expand_var "${service^^}_SERVICE_TITLE")
    if ! service_is_enabled "$service"; then
        error_msg "$title is not enabled"
        return 1
    fi
}

_service_print_detailed_status() {
    local service="$1"

    # indent output
    call_if_defined "${service}_print_status" | sed 's/^/  /'
}

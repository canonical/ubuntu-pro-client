# shellcheck disable=SC2039

check_user() {
    if [ "$(id -u)" -ne 0 ]; then
        error_msg "This command must be run as root (try using sudo)"
        exit 2
    fi
}

service_from_command() {
    local command="$1"

     echo "$command" | awk '
         /^is-.*-enabled$/ {
             match($0, /^is-(.*)-enabled$/, m);
             print m[1];
         }
         /^(enable|disable)-/ {
             match($0, /^(enable|disable)-(.*)/, m);
             print m[2];
         }
    '
}

service_enable() {
    local service="$1"
    local token="$2"

    check_user
    service_check_support "$service"
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

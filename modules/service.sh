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

    local service_upper
    service_upper=$(uppercase "$service")
    local name series archs
    name=$(expand_var "${service_upper}_SERVICE_NAME")
    series=$(expand_var "${service_upper}_SUPPORTED_SERIES")
    archs=$(expand_var "${service_upper}_SUPPORTED_ARCHS")
    check_service_support "$name" "$series" "$archs"
    call_if_defined "${service}_check_support"
}

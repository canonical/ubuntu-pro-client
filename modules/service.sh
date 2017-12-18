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

service_is_enabled() {
    local service="$1"

    "${service}_is_enabled"
}

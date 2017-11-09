# shellcheck disable=SC2039

validate_user_pass_token() {
    echo "$1" | grep -q '^[^:]\+:[^:]\+$'
}

check_token() {
    local repo_url="$1"
    local token="$2"

    echo -n 'Checking token... '

    if [ -x "$APT_HELPER" ]; then
        check_result check_url_with_token "$repo_url" "$token" \
                     "/dists/${SERIES}/Release"
    else
        echo 'SKIPPED'
    fi
}

check_url_with_token() {
    local repo_url="$1"
    local token="$2"
    local file="$3"

    local url
    url=$(private_repo_url "$repo_url" "$token" "$file")

    local discard log
    # apt-helper needs a filename to download to, which is just removed at the
    # end
    discard="$(mktemp)"
    log="$(mktemp)"
    if "$APT_HELPER" download-file "$url" "$discard" >"$log" 2>&1; then
        rm -f "$discard" "$log"
        return 0
    fi

    local error_line
    error_line=$(sed -n 's/^E: Failed to fetch [^ ]\+ \+//p' "$log")
    if echo "$error_line" | grep -q '^\(HttpError\)\?401'; then
        error_msg 'Invalid token'
    else
        error_msg "Failed checking token ($error_line)"
    fi

    rm -f "$discard" "$log"
    return 3
}

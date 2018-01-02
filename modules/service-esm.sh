# shellcheck disable=SC2034,SC2039

ESM_SERVICE_NAME="Extended Security Maintenance"
ESM_SUPPORTED_SERIES="precise"
ESM_SUPPORTED_ARCHS="ALL"

ESM_REPO_URL="esm.ubuntu.com"
ESM_REPO_KEY_FILE="ubuntu-esm-keyring.gpg"
ESM_REPO_LIST=${ESM_REPO_LIST:-"/etc/apt/sources.list.d/ubuntu-esm-${SERIES}.list"}

esm_enable() {
    local token="$1"

    check_token "$ESM_REPO_URL" "$token"
    apt_add_repo "$ESM_REPO_LIST" "$ESM_REPO_URL" "$token" \
                 "${KEYRINGS_DIR}/${ESM_REPO_KEY_FILE}"
    install_package_if_missing_file "$APT_METHOD_HTTPS" apt-transport-https
    install_package_if_missing_file "$CA_CERTIFICATES" ca-certificates
    echo -n 'Running apt-get update... '
    check_result apt_get update
    echo 'Ubuntu ESM repository enabled.'
}

esm_disable() {
    if [ -f "$ESM_REPO_LIST" ]; then
        apt_remove_repo "$ESM_REPO_LIST" "$ESM_REPO_URL" \
                        "$APT_KEYS_DIR/$ESM_REPO_KEY_FILE"
        echo -n 'Running apt-get update... '
        check_result apt_get update
        echo 'Ubuntu ESM repository disabled.'
    else
        echo 'Ubuntu ESM repository was not enabled.'
    fi
}

esm_is_enabled() {
    apt-cache policy | grep -Fq "$ESM_REPO_URL"
}

esm_validate_token() {
    local token="$1"

    if ! validate_user_pass_token "$token"; then
        error_msg 'Invalid token, it must be in the form "user:password"'
        return 1
    fi
}

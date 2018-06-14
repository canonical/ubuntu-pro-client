# shellcheck disable=SC2034,SC2039
 
CC_SERVICE_TITLE="Canonical Common Criteria"
CC_SUPPORTED_SERIES="xenial"
CC_SUPPORTED_ARCHS="x86_64 ppc64le s390x"

CC_REPO_URL="https://private-ppa.launchpad.net/fips-cc-stig/fipsdevppa"
CC_REPO_KEY_FILE="ubuntu-cc-keyring.gpg"
CC_REPO_LIST=${CC_REPO_LIST:-"/etc/apt/sources.list.d/ubuntu-cc-${SERIES}.list"}
CC_REPO_PREFERENCES=${CC_REPO_PREFERENCES:-"/etc/apt/preferences.d/ubuntu-cc-${SERIES}"}
CC_UBUNTU_COMMONCRITERIA="ubuntu-commoncriteria"

cc_install() {
    local token="$1"
    local result=0

    _cc_is_installed || result=$?
    if [ $result -eq 0 ]; then
        error_msg "Common Criteria artifacts already installed and available in /usr/lib/common-criteria."
        error_exit service_already_enabled
    fi

    check_token "$CC_REPO_URL" "$token"
    apt_add_repo "$CC_REPO_LIST" "$CC_REPO_URL" "$token" \
                 "${KEYRINGS_DIR}/${CC_REPO_KEY_FILE}"
    apt_install_package_if_missing_file "$APT_METHOD_HTTPS" apt-transport-https
    apt_install_package_if_missing_file "$CA_CERTIFICATES" ca-certificates
    echo -n 'Running apt-get update... '
    check_result apt_get update
    echo 'Ubuntu Common Criteria PPA repository enabled.'

    echo -n 'Installing Common Criteria artifacts (this may take a while)...'
    # shellcheck disable=SC2086
    check_result apt_get install $CC_UBUNTU_COMMONCRITERIA

    echo "Successfully installed Common Criteria artifacts. Please check in /usr/lib/common-criteria."
}

cc_enable() {
    not_supported 'Enabling CC'
}

cc_disable() {
    not_supported 'Disabling CC'
}

cc_is_enabled() {
    _cc_is_installed
}

cc_print_status() {
       echo "cc: artifacts are in /usr/lib/common-criteria"
}

_cc_is_installed() {
    apt_is_package_installed ubuntu-commoncriteria && return 0 
}

cc_validate_token() {
    local token="$1"

    if ! validate_user_pass_token "$token"; then
        error_msg 'Invalid token, it must be in the form "user:password"'
        return 1
    fi
}

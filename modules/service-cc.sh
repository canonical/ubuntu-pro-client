# shellcheck disable=SC2034,SC2039
 
CC_PROVISIONING_SERVICE_TITLE="Canonical Common Criteria EAL2 Provisioning"
CC_PROVISIONING_SUPPORTED_SERIES="xenial"
CC_PROVISIONING_SUPPORTED_ARCHS="x86_64 ppc64le s390x"

CC_PROVISIONING_REPO_URL="https://private-ppa.launchpad.net/ubuntu-advantage/commoncriteria"
CC_PROVISIONING_REPO_KEY_FILE="ubuntu-cc-keyring.gpg"
CC_PROVISIONING_REPO_LIST=${CC_PROVISIONING_REPO_LIST:-"/etc/apt/sources.list.d/ubuntu-cc-${SERIES}.list"}
CC_PROVISIONING_UBUNTU_COMMONCRITERIA="ubuntu-commoncriteria"

cc_provisioning_enable() {
    local token="$1"
    local result=0

    _cc_is_installed || result=$?
    if [ $result -eq 0 ]; then
        error_msg "Common Criteria artifacts are already installed and available in /usr/lib/common-criteria."
        error_exit service_already_enabled
    fi

    check_token "$CC_PROVISIONING_REPO_URL" "$token"
    apt_add_repo "$CC_PROVISIONING_REPO_LIST" "$CC_PROVISIONING_REPO_URL" "$token" \
                 "${KEYRINGS_DIR}/${CC_PROVISIONING_REPO_KEY_FILE}"
    apt_install_package_if_missing_file "$APT_METHOD_HTTPS" apt-transport-https
    apt_install_package_if_missing_file "$CA_CERTIFICATES" ca-certificates
    echo -n 'Running apt-get update... '
    check_result apt_get update
    echo 'Ubuntu Common Criteria PPA repository enabled.'

    echo -n 'Installing Common Criteria artifacts (this may take a while)... '
    # shellcheck disable=SC2086
    check_result apt_get install $CC_PROVISIONING_UBUNTU_COMMONCRITERIA

    echo "Successfully prepared this machine to host the Common Criteria artifacts."
    echo "Please follow instructions in /usr/share/doc/ubuntu-commoncriteria/README to configure EAL2 on the target machine(s)."
}

cc_provisioning_disable() {
    if [ -f "$CC_PROVISIONING_REPO_LIST" ]; then
        apt_remove_repo "$CC_PROVISIONING_REPO_LIST" "$CC_PROVISIONING_REPO_URL" \
                        "$APT_KEYS_DIR/$CC_PROVISIONING_REPO_KEY_FILE"
        echo -n 'Running apt-get update... '
        check_result apt_get update
        echo 'Canonical Common Criteria EAL2 Provisioning Disabled.'
    else
        echo 'Canonical Common Criteria EAL2 Provisioning is not Enabled.'
    fi

    if apt_is_package_installed $CC_PROVISIONING_UBUNTU_COMMONCRITERIA; then
        check_result apt_get remove $CC_PROVISIONING_UBUNTU_COMMONCRITERIA
        echo 'Canonical Common Criteria EAL2 Artifacts Removed.'
    fi
}

cc_provisioning_is_enabled() {
    _cc_is_installed
}

cc_provisioning_print_status() {
    echo "cc-provisioning: artifacts are in /usr/lib/common-criteria"
}

_cc_is_installed() {
    apt_is_package_installed ubuntu-commoncriteria && return 0 
}

cc_provisioning_validate_token() {
    local token="$1"

    if ! validate_user_pass_token "$token"; then
        error_msg 'Invalid token, it must be in the form "user:password"'
        return 1
    fi
}

# shellcheck disable=SC2034,SC2039
 
CISAUDIT_SERVICE_TITLE="Canonical CIS Benchmark 16.04 Audit Tool"
CISAUDIT_SUPPORTED_SERIES="xenial"
CISAUDIT_SUPPORTED_ARCHS="x86_64 ppc64le s390x"

CISAUDIT_REPO_URL="https://private-ppa.launchpad.net/ubuntu-advantage/security-benchmarks"
CISAUDIT_REPO_KEY_FILE="ubuntu-securitybenchmarks-keyring.gpg"
CISAUDIT_REPO_LIST=${CISAUDIT_REPO_LIST:-"/etc/apt/sources.list.d/ubuntu-cis-${SERIES}.list"}
CISAUDIT_UBUNTU_CISBENCHMARK="ubuntu-cisbenchmark-16.04"

cisaudit_enable() {
    local token="$1"
    local result=0

    _cisaudit_is_installed || result=$?
    if [ $result -eq 0 ]; then
        error_msg "CIS benchmark audit package is already installed and files are available in /usr/share/ubuntu-securityguides/$CISAUDIT_UBUNTU_CISBENCHMARK."
        error_exit service_already_enabled
    fi

    check_token "$CISAUDIT_REPO_URL" "$token"
    apt_add_repo "$CISAUDIT_REPO_LIST" "$CISAUDIT_REPO_URL" "$token" \
                 "${KEYRINGS_DIR}/${CISAUDIT_REPO_KEY_FILE}"
    apt_install_package_if_missing_file "$APT_METHOD_HTTPS" apt-transport-https
    apt_install_package_if_missing_file "$CA_CERTIFICATES" ca-certificates
    echo -n 'Running apt-get update... '
    check_result apt_get update
    echo 'Ubuntu Security Benchmarks PPA repository enabled.'

    echo -n 'Installing CIS audit benchmark tool (this may take a while)... '
    # shellcheck disable=SC2086
    check_result apt_get install $CISAUDIT_UBUNTU_CISBENCHMARK

    echo "Successfully installed the CIS audit tool."
    echo "Please follow instructions in /usr/share/doc/$CISAUDIT_UBUNTU_CISBENCHMARK/README to run the CIS audit tool on the target machine(s)."
}

cisaudit_disable() {
    if [ -f "$CISAUDIT_REPO_LIST" ]; then
        apt_remove_repo "$CISAUDIT_REPO_LIST" "$CISAUDIT_REPO_URL" \
                        "$APT_KEYS_DIR/$CISAUDIT_REPO_KEY_FILE"
        echo -n 'Running apt-get update... '
        check_result apt_get update
        echo "Canonical CIS Benchmark 16.04 Audit Tool Repository Disabled."
    else
        echo 'Canonical CIS Benchmark 16.04 Audit Tool Repository is not Enabled.'
    fi

    if apt_is_package_installed $CISAUDIT_UBUNTU_CISBENCHMARK; then
        check_result apt_get remove $CISAUDIT_UBUNTU_CISBENCHMARK
        echo 'Canonical CIS Benchmark 16.04 Audit Tool Removed.'
    fi
}

cisaudit_is_enabled() {
    _cisaudit_is_installed
}

cisaudit_print_status() {
    echo "cisaudit: files are in /usr/share/ubuntu-securityguides/$CISAUDIT_UBUNTU_CISBENCHMARK"
}

_cisaudit_is_installed() {
    apt_is_package_installed $CISAUDIT_UBUNTU_CISBENCHMARK && return 0 
}

cisaudit_validate_token() {
    local token="$1"

    if ! validate_user_pass_token "$token"; then
        error_msg 'Invalid token, it must be in the form "user:password"'
        return 1
    fi
}

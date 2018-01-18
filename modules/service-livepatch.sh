# shellcheck disable=SC2034,SC2039

LIVEPATCH_SERVICE_TITLE="Canonical Livepatch"
LIVEPATCH_SUPPORTED_SERIES="trusty xenial"
LIVEPATCH_SUPPORTED_ARCHS="x86_64"

livepatch_enable() {
    local token="$1"

    _livepatch_install_prereqs
    if ! livepatch_is_enabled; then
        if check_snapd_kernel_support; then
            echo 'Enabling Livepatch with the given token, stand by...'
            canonical-livepatch enable "$token"
        else
            echo
            echo "Your currently running kernel ($KERNEL_VERSION) is too old to"
            echo "support snaps. Version 4.4.0 or higher is needed."
            echo
            echo "Please reboot your system into a supported kernel version"
            echo "and run the following command one more time to complete the"
            echo "installation:"
            echo
            echo "sudo $SCRIPTNAME enable-livepatch $token"
            exit 5
        fi
    else
        echo 'Livepatch already enabled.'
    fi
    echo 'Use "canonical-livepatch status" to verify current patch status.'
}

livepatch_disable() {
    if livepatch_is_enabled; then
        echo 'Disabling Livepatch...'
        canonical-livepatch disable
        if [ "$1" = "yes" ]; then
            echo 'Removing the canonical-livepatch snap...'
            snap remove canonical-livepatch
        else
            echo 'Note: the canonical-livepatch snap is still installed.'
            echo 'To remove it, run sudo snap remove canonical-livepatch'
        fi
    else
        echo 'Livepatch is already disabled.'
    fi
}

livepatch_is_enabled() {
    # Explicitly return 1 for the case where the command is not found.
    canonical-livepatch status >/dev/null 2>&1 || return 1
}

livepatch_validate_token() {
    local token="$1"

    if ! _livepatch_validate_token "$token"; then
        error_msg "Invalid or missing Livepatch token"
        error_msg "Please visit https://ubuntu.com/livepatch to obtain a Livepatch token."
        return 1
    fi
}

_livepatch_validate_token() {
    local token="$1"

    # the livepatch token is an hex string 32 characters long
    echo "$token" | grep -q -E '^[0-9a-fA-F]{32}$'
}

_livepatch_install_prereqs() {
    install_package_if_missing_file "$SNAPD" snapd
    if ! snap list canonical-livepatch >/dev/null 2>&1; then
        echo 'Installing the canonical-livepatch snap.'
        echo 'This may take a few minutes depending on your bandwidth.'
        # show output as it has a nice progress bar and isn't too verbose
        snap install canonical-livepatch
    fi
}

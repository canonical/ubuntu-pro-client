# shellcheck disable=SC2039

private_repo_url() {
    local repo_url="$1"
    local credentials="$2"
    local file="$3"
    echo "https://${credentials}@${repo_url}/ubuntu${file}"
}

package_version() {
    [ -z "$1" ] && return 1
    dpkg-query -W -f '${Version}\n' "$1" 2>/dev/null
}

# Write an APT sources file
write_apt_list_file() {
    local repo_file="$1"
    local repo_url="$2"
    local credentials="$3"

    cat >"$repo_file" <<EOF
deb https://${credentials}@${repo_url}/ubuntu ${SERIES} main
# deb-src https://${credentials}@${repo_url}/ubuntu ${SERIES} main
EOF
}

apt_get() {
    DEBIAN_FRONTEND=noninteractive \
                   apt-get -y -o Dpkg::Options::='--force-confold' "$@"
}

is_package_installed() {
    dpkg-query -s "$1" >/dev/null 2>&1
}

# Install a package if the specified file doesn't exist
install_package_if_missing_file() {
    local file="$1"
    local package="$2"

    if [ ! -f "$file" ]; then
        echo -n "Installing missing dependency $package... "
        check_result apt_get install "$package"
    fi
}

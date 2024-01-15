Feature: API security/security status tests

    @uses.config.contract_token
    Scenario: Call Livepatched CVEs endpoint
        Given a `xenial` `lxd-vm` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro api u.pro.security.status.livepatch_cves.v1` as non-root
        Then stdout matches regexp:
         """
         {"name": "cve-2013-1798", "patched": true}
         """
         And stdout matches regexp:
         """
         "type": "LivepatchCVEs"
         """

    @uses.config.contract_token
    Scenario Outline: Call package manifest endpoint for machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that `esm-infra` is enabled
        When I apt upgrade
        And I apt install `jq bzip2`
        # Install the oscap version 1.3.7 which solved the epoch error message issue
        And I apt install `cmake libdbus-1-dev libdbus-glib-1-dev libcurl4-openssl-dev libgcrypt20-dev libselinux1-dev libxslt1-dev libgconf2-dev libacl1-dev libblkid-dev libcap-dev libxml2-dev libldap2-dev libpcre3-dev swig libxml-parser-perl libxml-xpath-perl libperl-dev libbz2-dev g++ libapt-pkg-dev libyaml-dev libxmlsec1-dev libxmlsec1-openssl`
        And I run `wget https://github.com/OpenSCAP/openscap/releases/download/1.3.7/openscap-1.3.7.tar.gz` as non-root
        And I run `tar xzf openscap-1.3.7.tar.gz` as non-root
        And I run shell command `mkdir -p openscap-1.3.7/build` as non-root
        And I run shell command `cd openscap-1.3.7/build/ && cmake ..` with sudo
        And I run shell command `cd openscap-1.3.7/build/ && make` with sudo
        And I run shell command `cd openscap-1.3.7/build/ && make install` with sudo
        # Installs its shared libs in /usr/local/lib/
        And I run `ldconfig` with sudo
        And I run shell command `pro api u.security.package_manifest.v1 | jq -r '.data.attributes.manifest_data' > manifest` as non-root
        And I run shell command `wget https://security-metadata.canonical.com/oval/oci.com.ubuntu.<release>.usn.oval.xml.bz2` as non-root
        And I run `bunzip2 oci.com.ubuntu.<release>.usn.oval.xml.bz2` as non-root
        And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
        Then stdout matches regexp:
        """
        oval:com.ubuntu.<release>:def:<CVE_ID>:\s+false
        """
        # Trigger CVE https://ubuntu.com/security/CVE-2018-10846 with ID 39991000000 in OVAL data (<release> == Xenial $ Bionic)
        # Trigger CVE https://ubuntu.com/security/CVE-2022-2509 with ID 55501000000 in OVAL data (<release> > Xenial)
        When I run shell command `sed -i -E 's/libgnutls30:amd64\s+.*/libgnutls30:amd64 <base_version>/' manifest` as non-root
        And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
        Then stdout matches regexp:
        """
        oval:com.ubuntu.<release>:def:<CVE_ID>:\s+true
        """
        # Update the manifest
        When I run shell command `pro api u.security.package_manifest.v1 | jq -r '.data.attributes.manifest_data' > manifest` as non-root
        And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
        Then stdout matches regexp:
        """
        oval:com.ubuntu.<release>:def:<CVE_ID>:\s+false
        """
        # Downgrade the package 
        When I apt install `libgnutls30=<base_version>`
        And I run shell command `pro api u.security.package_manifest.v1 | jq -r '.data.attributes.manifest_data' > manifest` as non-root
        And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
        Then stdout matches regexp:
        """
        oval:com.ubuntu.<release>:def:<CVE_ID>:\s+true
        """
        Examples: ubuntu release
            | release | machine_type  | base_version    | CVE_ID      |
            | xenial  | lxd-container | 3.4.10-4ubuntu1 | 39991000000 |
            | bionic  | lxd-container | 3.5.18-1ubuntu1 | 55501000000 |
            | focal   | lxd-container | 3.6.13-2ubuntu1 | 55501000000 |
            | jammy   | lxd-container | 3.7.3-4ubuntu1  | 55501000000 |

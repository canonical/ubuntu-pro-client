Feature: API security/security status tests

    @series.xenial
    @uses.config.machine_type.lxd.vm
    @uses.config.contract_token
    Scenario: Call Livepatched CVEs endpoint
        Given a `xenial` machine with ubuntu-advantage-tools installed
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

    @series.lts
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token
    Scenario Outline: Call package manifest endpoint for machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-infra       +yes      +enabled  +Expanded Security Maintenance for Infrastructure
        """
        When I run `apt update` with sudo
        And I run `apt upgrade -y` with sudo
        And I run `apt install jq bzip2 -y` with sudo
        # Install the oscap version 1.3.7 which solved the epoch error message issue
        And I run `apt-get install lcov swig xsltproc rpm-common lua5.3 libyaml-dev libapt-pkg-dev libdbus-1-dev libdbus-glib-1-dev libcurl4-openssl-dev libgcrypt-dev libselinux1-dev libgconf2-dev libacl1-dev libblkid-dev libcap-dev libxml2-dev libxslt1-dev libxml-parser-perl libxml-xpath-perl libperl-dev librpm-dev librtmp-dev libxmlsec1-dev libxmlsec1-openssl cmake make build-essential -y` with sudo
        And I run `apt-get remove *rpm* -y` with sudo
        And I run `wget https://github.com/OpenSCAP/openscap/releases/download/1.3.7/openscap-1.3.7.tar.gz` as non-root
        And I run `tar xzf openscap-1.3.7.tar.gz` as non-root
        And I run shell command `cd openscap-1.3.7/ && mkdir build && cd build/` as non-root
        And I run shell command `cd openscap-1.3.7/build/ && cmake -DCMAKE_BUILD_TYPE=RelWithDebInfo ../ && make install` with sudo
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
        When I run shell command `apt install libgnutls30=<base_version> -y --allow-downgrades` with sudo
        And I run shell command `pro api u.security.package_manifest.v1 | jq -r '.data.attributes.manifest_data' > manifest` as non-root
        And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
        Then stdout matches regexp:
        """
        oval:com.ubuntu.<release>:def:<CVE_ID>:\s+true
        """
        

        Examples: ubuntu release
            | release | base_version    | CVE_ID      |
            | xenial  | 3.4.10-4ubuntu1 | 39991000000 |
            | bionic  | 3.5.18-1ubuntu1 | 55501000000 |
            | focal   | 3.6.13-2ubuntu1 | 55501000000 |
            | jammy   | 3.7.3-4ubuntu1  | 55501000000 |

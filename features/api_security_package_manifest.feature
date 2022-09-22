Feature: API security status package list in manifest format

    @series.lts
    @uses.config.machine_type.lxd.container
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
        And I run `apt install jq bzip2 libopenscap8 -y` with sudo
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

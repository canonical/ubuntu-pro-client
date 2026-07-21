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
    And I install the oscap tool
    And I run shell command `pro api u.security.package_manifest.v1 | jq -r '.data.attributes.manifest_data' > manifest` as non-root
    And I run shell command `wget https://security-metadata.canonical.com/oval/oci.com.ubuntu.<release>.usn.oval.xml.bz2` as non-root
    And I run `bunzip2 oci.com.ubuntu.<release>.usn.oval.xml.bz2` as non-root
    And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
    Then stdout matches regexp:
      """
      oval:com.ubuntu.<release>:def:<oval_def_id>:\s+false
      """
    # Trigger CVE https://ubuntu.com/security/CVE-2018-10846 with ID 39991000000 in OVAL data (<release> == Xenial $ Bionic)
    # Trigger CVE https://ubuntu.com/security/CVE-2022-2509 with ID 55501000000 in OVAL data (<release> > Xenial)
    When I run shell command `sed -i -E 's/<manifest_pattern>\s+.*/<manifest_pattern> <forced_vulnerable_version>/' manifest` as non-root
    And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
    Then stdout matches regexp:
      """
      oval:com.ubuntu.<release>:def:<oval_def_id>:\s+true
      """
    # Update the manifest
    When I run shell command `pro api u.security.package_manifest.v1 | jq -r '.data.attributes.manifest_data' > manifest` as non-root
    And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
    Then stdout matches regexp:
      """
      oval:com.ubuntu.<release>:def:<oval_def_id>:\s+false
      """
    # Downgrade the package
    When I apt install `<package_name>=<forced_vulnerable_version>`
    And I run shell command `pro api u.security.package_manifest.v1 | jq -r '.data.attributes.manifest_data' > manifest` as non-root
    And I run shell command `oscap oval eval --report report.html oci.com.ubuntu.<release>.usn.oval.xml` as non-root
    Then stdout matches regexp:
      """
      oval:com.ubuntu.<release>:def:<oval_def_id>:\s+true
      """

    Examples: ubuntu release
      | release | machine_type  | package_name | manifest_pattern  | forced_vulnerable_version | oval_def_id  |
      | xenial  | lxd-container | libgnutls30  | libgnutls30:amd64 | 3.4.10-4ubuntu1           | 39991000000  |
      | bionic  | lxd-container | libgnutls30  | libgnutls30:amd64 | 3.5.18-1ubuntu1           | 555010000000 |
      | focal   | lxd-container | libgnutls30  | libgnutls30:amd64 | 3.6.13-2ubuntu1           | 555010000000 |
      | jammy   | lxd-container | libgnutls30  | libgnutls30:amd64 | 3.7.3-4ubuntu1            | 555010000000 |

# TODO(srunde3): refactor test to work with Noble+. libgnutls30 is not available there.

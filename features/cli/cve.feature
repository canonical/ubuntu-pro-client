Feature: CLI cve command

  @uses.config.contract_token
  Scenario Outline: cve command for a kernel CVE
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I push static file `security_issues_focal.json.xz` to machine
    And I create the file `/tmp/response-overlay.json` with the following:
      """
      {
        "https://security-metadata.canonical.com/oval/com.ubuntu.focal.pkg.json.xz": [
          {
            "code": 200,
            "response": {
              "file_path": "/tmp/security_issues_focal.json.xz"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I run `pro cve CVE-2023-20569` as non-root
    Then stdout matches regexp:
      """
      name:            CVE-2023-20569
      public-url:      https://ubuntu.com/security/CVE-2023-20569
      published-at:    2023-08-08
      cve-cache-date:  .*
      apt-cache-date:  .*
      priority:        .*high.*
      cvss-score:      4.7
      cvss-severity:   medium
      description: |
        A side channel vulnerability on some of the AMD CPUs may allow an attacker to
        influence the return address prediction. This may result in speculative
        execution at an attacker-controlled address, potentially leading to
        information disclosure.
      notes:
        - alexmurray> The listed microcode revisions for 3rd Gen AMD EPYC processors
          in AMD-SB-7005 were provided to the upstream linux-firmware repo in commit
          b250b32ab1d044953af2dc5e790819a7703b7ee6 whilst the 4th Gen microcode was
          provided in commit f2eb058afc57348cde66852272d6bf11da1eef8f. This is not
          planned to be fixed for the amd64-microcode package in Ubuntu 14.04 as that
          release was already outside of the LTS timeframe when this hardware platform
          was launched.
        - ijwhitfield> Backports for 5.4 and earlier kernels are not planned due to a
          large number of dependency commits and having already backported patches to
          the AMD microcode package.
      affected_packages:
        linux-headers-5.4.0-1131-kvm:  vulnerable
        linux-kvm-headers-5.4.0-1131:  vulnerable
        linux-modules-5.4.0-1131-kvm:  vulnerable
      """

    Examples: ubuntu release
      | release | machine_type |
      | focal   | lxd-vm       |

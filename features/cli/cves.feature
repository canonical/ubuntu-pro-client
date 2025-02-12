Feature: CLI cves command

  @uses.config.contract_token
  Scenario Outline: Cves command on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro cves` as non-root
    And I push static file `security_issues_xenial.json.xz` to machine
    And I create the file `/tmp/response-overlay.json` with the following:
      """
      {
        "https://security-metadata.canonical.com/oval/com.ubuntu.xenial.pkg.json.xz": [
          {
            "code": 200,
            "response": {
              "file_path": "/tmp/security_issues_xenial.json.xz"
            }
          }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
        serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I run `pro cves` as non-root
    Then I will see the following on stdout:
      """
      Package              Priority  Origin     Vulnerability
      accountsservice      medium    esm-infra  CVE-2023-3297
      accountsservice      low       -          CVE-2012-6655
      bash                 low       esm-infra  CVE-2019-18276
      libaccountsservice0  medium    esm-infra  CVE-2023-3297
      libaccountsservice0  low       -          CVE-2012-6655
      """
    When I run `pro cves --fixable` as non-root
    Then I will see the following on stdout:
      """
      Package              Priority  Origin     Vulnerability
      accountsservice      medium    esm-infra  CVE-2023-3297
      bash                 low       esm-infra  CVE-2019-18276
      libaccountsservice0  medium    esm-infra  CVE-2023-3297
      """
    When I run `pro cves --unfixable` as non-root
    Then I will see the following on stdout:
      """
      Package              Priority  Origin  Vulnerability
      accountsservice      low       -       CVE-2012-6655
      libaccountsservice0  low       -       CVE-2012-6655
      """
    When I apt install `bash accountsservice libaccountsservice0`
    And I run `pro cves` as non-root
    Then I will see the following on stdout:
      """
      Package              Priority  Origin  Vulnerability
      accountsservice      low       -       CVE-2012-6655
      libaccountsservice0  low       -       CVE-2012-6655
      """
    When I run `pro cves --fixable` as non-root
    Then I will see the following on stdout:
      """
      No fixable CVES found that affect this system
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

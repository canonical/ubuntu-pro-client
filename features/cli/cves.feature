Feature: CLI cves command

  @uses.config.contract_token
  Scenario Outline: cve command for fixable esm-apps issues
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I push static file `security_issues_jammy.json.xz` to machine
    And I create the file `/tmp/response-overlay.json` with the following:
      """
      {
      "https://security-metadata.canonical.com/oval/com.ubuntu.jammy.pkg.json.xz": [
      {
      "code": 200,
      "response": {
      "file_path": "/tmp/security_issues_jammy.json.xz"
      }
      }]
      }
      """
    And I append the following on uaclient config:
      """
      features:
      serviceclient_url_responses: "/tmp/response-overlay.json"
      """
    And I apt install `nodejs`
    When I run `pro cves` as non-root
    Then stdout matches regexp:
      """
      libnode72 +high +esm-apps +CVE-2023-44487
      """
    And stdout matches regexp:
      """
      nodejs +high +esm-apps +CVE-2023-44487
      """
    And stdout matches regexp:
      """
      nodejs-doc +high +- +CVE-2023-44487
      """
    When I run `pro cves --fixable` as non-root
    Then stdout matches regexp:
      """
      libnode72 +high +esm-apps +CVE-2023-44487
      """
    And stdout matches regexp:
      """
      nodejs +high +esm-apps +CVE-2023-44487
      """
    And stdout does not match regexp:
      """
      nodejs-doc +high +- +CVE-2023-44487
      """
    When I run `pro cves --unfixable` as non-root
    Then stdout does not match regexp:
      """
      libnode72 +high +esm-apps +CVE-2023-44487
      """
    And stdout does not match regexp:
      """
      nodejs +high +esm-apps +CVE-2023-44487
      """
    And stdout matches regexp:
      """
      nodejs-doc +high +- +CVE-2023-44487
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

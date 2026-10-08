Feature: CLI usns command

  @uses.config.contract_token
  Scenario Outline: usns command on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I push static file `security_issues_jammy.json.xz` to machine
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
    And I apt install `python3-urllib3`
    And I run `pro usns` as non-root
    Then I will see the following on stdout:
      """
      Package          Priority  Origin     Vulnerability
      python3-urllib3  high      esm-infra  USN-7927-1
      python3-urllib3  high      esm-infra  USN-7927-2
      python3-urllib3  high      esm-infra  USN-7927-3
      """
    When I run `pro usns --fixable` as non-root
    Then I will see the following on stdout:
      """
      Package          Priority  Origin     Vulnerability
      python3-urllib3  high      esm-infra  USN-7927-1
      python3-urllib3  high      esm-infra  USN-7927-2
      python3-urllib3  high      esm-infra  USN-7927-3
      """
    When I run `pro usns --unfixable` as non-root
    Then I will see the following on stdout:
      """
      No unfixable USNs found that affect this system
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

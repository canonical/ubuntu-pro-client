Feature: v1 security usns API endpoint

  @uses.config.contract_token
  Scenario Outline: USN vulnerabilities for a jammy machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro api u.pro.security.usns.v1` as non-root
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
    And I run `pro api u.pro.security.usns.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "packages": {
            "python3-urllib3": {
              "current_version": ".*",
              "usns": [
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "2.0.7-1ubuntu0.1",
                  "name": "USN-7927-1"
                },
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "2.0.7-1ubuntu0.2",
                  "name": "USN-7927-2"
                },
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "2.0.7-1ubuntu0.3",
                  "name": "USN-7927-3"
                }
              ]
            }
          },
          "usns": {
            "USN-7927-1": {
              "affected_packages": [
                "python3-urllib3"
              ],
              "description": "It was discovered that urllib3 incorrectly handled certain inputs.\nAn attacker could possibly use this issue to bypass certain proxy\nrestrictions.",
              "notes": [],
              "priority": "high",
              "published_at": ".*",
              "related_cves": [
                "CVE-2025-66418",
                "CVE-2025-66471"
              ],
              "revision": 1,
              "superseded_by": "USN-7927-2",
              "title": "urllib3 vulnerabilities",
              "updated_at": ".*"
            },
            "USN-7927-2": {
              "affected_packages": [
                "python3-urllib3"
              ],
              "description": "USN-7927-1 fixed vulnerabilities in urllib3. Unfortunately this\nintroduced a regression. This update fixes the problem.",
              "notes": [],
              "priority": "high",
              "published_at": ".*",
              "related_cves": [
                "CVE-2025-66471"
              ],
              "revision": 2,
              "superseded_by": "USN-7927-3",
              "title": "urllib3 regression",
              "updated_at": ".*"
            },
            "USN-7927-3": {
              "affected_packages": [
                "python3-urllib3"
              ],
              "description": "USN-7927-2 introduced a regression in urllib3. This update\nfixes the problem.",
              "notes": [],
              "priority": "high",
              "published_at": ".*",
              "related_cves": [
                "CVE-2025-66471"
              ],
              "revision": 3,
              "superseded_by": null,
              "title": "urllib3 regression",
              "updated_at": null
            }
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNs"
      }
      """
    When I run `pro api u.pro.security.usns.v1 --data '{"unfixable": true}'` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "packages": {},
          "usns": {}
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNs"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

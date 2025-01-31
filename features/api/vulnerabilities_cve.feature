Feature: Client behaviour for CVE vulnerabilities API

  @uses.config.contract_token
  Scenario Outline: CVE vulnerabilities for xenial machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    # Check we can download and parse the JSON data
    And I run `pro api u.pro.security.vulnerabilities.cve.v1` as non-root
    And I verify that running `pro api u.pro.security.vulnerabilities.cve.v1 --data '{"fixable": true, "unfixable": true}'` `as non-root` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "invalid-option-combination",
          "meta": {
            "option1": "unfixable",
            "option2": "fixable"
          },
          "title": "Error: Cannot use unfixable together with fixable."
        }
      ]
      """
    When I push static file `security_issues_xenial.json.xz` to machine
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
    And I run `pro api u.pro.security.vulnerabilities.cve.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": ".*",
          "cves": {
            "CVE-2012-6655": {
              "cvss_score": 3.3,
              "cvss_severity": "low",
              "description": "An issue exists AccountService 0.6.37 in the\nuser_change_password_authorized_cb() function in user.c which could let a\nlocal users obtain encrypted passwords.",
              "notes": [],
              "priority": "low",
              "published_at": ".*",
              "related_packages": [
                "accountsservice"
              ],
              "related_usns": [
                {
                  "name": "USN-6687-1",
                  "title": ""
                }
              ]
            },
            "CVE-2019-18276": {
              "cvss_score": 7.8,
              "cvss_severity": "high",
              "description": "An issue was discovered in disable_priv_mode in shell.c in GNU Bash through\n5.0 patch 11. By default, if Bash is run with its effective UID not equal\nto its real UID, it will drop privileges by setting its effective UID to\nits real UID. However, it does so incorrectly. On Linux and other systems\nthat support \\"saved UID\\" functionality, the saved UID is not dropped. An\nattacker with command execution in the shell can use \\"enable -f\\" for\nruntime loading of a new builtin, which can be a shared object that calls\nsetuid() and therefore regains privileges. However, binaries running with\nan effective UID of 0 are unaffected.",
              "notes": [
                "sbeattie> This issue appears to only affect bash when bash is\nsetuid. Ubuntu does not ship with bash setuid, so this has minimal\nimpact for Ubuntu users. This is why we have rated the priority\nfor this issue 'low'.\nreproducer steps in the suse bugzilla"
              ],
              "priority": "low",
              "published_at": ".*",
              "related_packages": [
                "bash"
              ],
              "related_usns": [
                {
                  "name": "USN-5380-1",
                  "title": "Bash vulnerability"
                }
              ]
            },
            "CVE-2023-3297": {
              "cvss_score": 8.1,
              "cvss_severity": "high",
              "description": "In Ubuntu's accountsservice an unprivileged local attacker can trigger a\nuse-after-free vulnerability in accountsservice by sending a D-Bus message\nto the accounts-daemon process.",
              "notes": [
                "mdeslaur> This is GHSL-2023-139\nIssue is in the Ubuntu-specific 0010-set-language.patch patch.",
                "eslerm> CWE-416"
              ],
              "priority": "medium",
              "published_at": ".*",
              "related_packages": [
                "accountsservice"
              ],
              "related_usns": [
                {
                  "name": "USN-6190-1",
                  "title": ""
                },
                {
                  "name": "USN-6190-2",
                  "title": "AccountsService vulnerability"
                }
              ]
            }
          },
          "packages": {
            "accountsservice": {
              "current_version": "0.6.40-2ubuntu11.6",
              "cves": [
                {
                  "fix_origin": null,
                  "fix_status": "vulnerable",
                  "fix_version": null,
                  "name": "CVE-2012-6655"
                },
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "0.6.40-2ubuntu11.6\+esm1",
                  "name": "CVE-2023-3297"
                }
              ]
            },
            "bash": {
              "current_version": "4.3-14ubuntu1.4",
              "cves": [
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "4.3-14ubuntu1.4\+esm1",
                  "name": "CVE-2019-18276"
                }
              ]
            },
            "libaccountsservice0": {
              "current_version": "0.6.40-2ubuntu11.6",
              "cves": [
                {
                  "fix_origin": null,
                  "fix_status": "vulnerable",
                  "fix_version": null,
                  "name": "CVE-2012-6655"
                },
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "0.6.40-2ubuntu11.6\+esm1",
                  "name": "CVE-2023-3297"
                }
              ]
            }
          },
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEVulnerabilities"
      }
      """
    When I run `pro api u.pro.security.vulnerabilities.cve.v1 --data '{"unfixable": true}'` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": ".*",
          "cves": {
            "CVE-2012-6655": {
              "cvss_score": 3.3,
              "cvss_severity": "low",
              "description": "An issue exists AccountService 0.6.37 in the\nuser_change_password_authorized_cb() function in user.c which could let a\nlocal users obtain encrypted passwords.",
              "notes": [],
              "priority": "low",
              "published_at": ".*",
              "related_packages": [
                "accountsservice"
              ],
              "related_usns": [
                {
                  "name": "USN-6687-1",
                  "title": ""
                }
              ]
            }
          },
          "packages": {
            "accountsservice": {
              "current_version": "0.6.40-2ubuntu11.6",
              "cves": [
                {
                  "fix_origin": null,
                  "fix_status": "vulnerable",
                  "fix_version": null,
                  "name": "CVE-2012-6655"
                }
              ]
            },
            "libaccountsservice0": {
              "current_version": "0.6.40-2ubuntu11.6",
              "cves": [
                {
                  "fix_origin": null,
                  "fix_status": "vulnerable",
                  "fix_version": null,
                  "name": "CVE-2012-6655"
                }
              ]
            }
          },
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEVulnerabilities"
      }
      """
    When I run `pro api u.pro.security.vulnerabilities.cve.v1 --data '{"fixable": true}'` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": ".*",
          "cves": {
            "CVE-2019-18276": {
              "cvss_score": 7.8,
              "cvss_severity": "high",
              "description": "An issue was discovered in disable_priv_mode in shell.c in GNU Bash through\n5.0 patch 11. By default, if Bash is run with its effective UID not equal\nto its real UID, it will drop privileges by setting its effective UID to\nits real UID. However, it does so incorrectly. On Linux and other systems\nthat support \\"saved UID\\" functionality, the saved UID is not dropped. An\nattacker with command execution in the shell can use \\"enable -f\\" for\nruntime loading of a new builtin, which can be a shared object that calls\nsetuid() and therefore regains privileges. However, binaries running with\nan effective UID of 0 are unaffected.",
              "notes": [
                "sbeattie> This issue appears to only affect bash when bash is\nsetuid. Ubuntu does not ship with bash setuid, so this has minimal\nimpact for Ubuntu users. This is why we have rated the priority\nfor this issue 'low'.\nreproducer steps in the suse bugzilla"
              ],
              "priority": "low",
              "published_at": ".*",
              "related_packages": [
                "bash"
              ],
              "related_usns": [
                {
                  "name": "USN-5380-1",
                  "title": "Bash vulnerability"
                }
              ]
            },
            "CVE-2023-3297": {
              "cvss_score": 8.1,
              "cvss_severity": "high",
              "description": "In Ubuntu's accountsservice an unprivileged local attacker can trigger a\nuse-after-free vulnerability in accountsservice by sending a D-Bus message\nto the accounts-daemon process.",
              "notes": [
                "mdeslaur> This is GHSL-2023-139\nIssue is in the Ubuntu-specific 0010-set-language.patch patch.",
                "eslerm> CWE-416"
              ],
              "priority": "medium",
              "published_at": ".*",
              "related_packages": [
                "accountsservice"
              ],
              "related_usns": [
                {
                  "name": "USN-6190-1",
                  "title": ""
                },
                {
                  "name": "USN-6190-2",
                  "title": "AccountsService vulnerability"
                }
              ]
            }
          },
          "packages": {
            "accountsservice": {
              "current_version": "0.6.40-2ubuntu11.6",
              "cves": [
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "0.6.40-2ubuntu11.6\+esm1",
                  "name": "CVE-2023-3297"
                }
              ]
            },
            "bash": {
              "current_version": "4.3-14ubuntu1.4",
              "cves": [
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "4.3-14ubuntu1.4\+esm1",
                  "name": "CVE-2019-18276"
                }
              ]
            },
            "libaccountsservice0": {
              "current_version": "0.6.40-2ubuntu11.6",
              "cves": [
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "0.6.40-2ubuntu11.6\+esm1",
                  "name": "CVE-2023-3297"
                }
              ]
            }
          },
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEVulnerabilities"
      }
      """
    When I apt install `accountsservice`
    And I run `pro api u.pro.security.vulnerabilities.cve.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "apt_updated_at": ".*",
          "cves": {
            "CVE-2012-6655": {
              "cvss_score": 3.3,
              "cvss_severity": "low",
              "description": "An issue exists AccountService 0.6.37 in the\nuser_change_password_authorized_cb() function in user.c which could let a\nlocal users obtain encrypted passwords.",
              "notes": [],
              "priority": "low",
              "published_at": ".*",
              "related_packages": [
                "accountsservice"
              ],
              "related_usns": [
                {
                  "name": "USN-6687-1",
                  "title": ""
                }
              ]
            },
            "CVE-2019-18276": {
              "cvss_score": 7.8,
              "cvss_severity": "high",
              "description": "An issue was discovered in disable_priv_mode in shell.c in GNU Bash through\n5.0 patch 11. By default, if Bash is run with its effective UID not equal\nto its real UID, it will drop privileges by setting its effective UID to\nits real UID. However, it does so incorrectly. On Linux and other systems\nthat support \\"saved UID\\" functionality, the saved UID is not dropped. An\nattacker with command execution in the shell can use \\"enable -f\\" for\nruntime loading of a new builtin, which can be a shared object that calls\nsetuid() and therefore regains privileges. However, binaries running with\nan effective UID of 0 are unaffected.",
              "notes": [
                "sbeattie> This issue appears to only affect bash when bash is\nsetuid. Ubuntu does not ship with bash setuid, so this has minimal\nimpact for Ubuntu users. This is why we have rated the priority\nfor this issue 'low'.\nreproducer steps in the suse bugzilla"
              ],
              "priority": "low",
              "published_at": ".*",
              "related_packages": [
                "bash"
              ],
              "related_usns": [
                {
                  "name": "USN-5380-1",
                  "title": "Bash vulnerability"
                }
              ]
            }
          },
          "packages": {
            "accountsservice": {
              "current_version": "0.6.40-2ubuntu11.6\+esm1",
              "cves": [
                {
                  "fix_origin": null,
                  "fix_status": "vulnerable",
                  "fix_version": null,
                  "name": "CVE-2012-6655"
                }
              ]
            },
            "bash": {
              "current_version": "4.3-14ubuntu1.4",
              "cves": [
                {
                  "fix_origin": "esm-infra",
                  "fix_status": "fixed",
                  "fix_version": "4.3-14ubuntu1.4\+esm1",
                  "name": "CVE-2019-18276"
                }
              ]
            },
            "libaccountsservice0": {
              "current_version": "0.6.40-2ubuntu11.6\+esm1",
              "cves": [
                {
                  "fix_origin": null,
                  "fix_status": "vulnerable",
                  "fix_version": null,
                  "name": "CVE-2012-6655"
                }
              ]
            }
          },
          "vulnerability_data_published_at": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEVulnerabilities"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

Feature: Fix plan API endpoints

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-1800-123456"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": null,
                "description": null,
                "error": {
                  "code": "security-fix-not-found-issue",
                  "msg": "Error: CVE-1800-123456 not found."
                },
                "expected_status": "error",
                "plan": [],
                "title": "CVE-1800-123456",
                "warnings": []
              }
            ],
            "expected_status": "error"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-123455"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "error",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {},
                  "affected_packages": null,
                  "description": null,
                  "error": {
                    "code": "invalid-security-issue",
                    "msg": "Error: issue \\"USN-123455\\" is not recognized.\n\nCVEs should follow the pattern CVE-yyyy-nnn.\n\nUSNs should follow the pattern USN-nnnn."
                  },
                  "expected_status": "error",
                  "plan": [],
                  "title": "USN-123455",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-123455", "CVE-12"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": null,
                "description": null,
                "error": {
                  "code": "invalid-security-issue",
                  "msg": "Error: issue \\"CVE-123455\\" is not recognized.\n\nCVEs should follow the pattern CVE-yyyy-nnn.\n\nUSNs should follow the pattern USN-nnnn."
                },
                "expected_status": "error",
                "plan": [],
                "title": "CVE-123455",
                "warnings": []
              },
              {
                "additional_data": {},
                "affected_packages": null,
                "description": null,
                "error": {
                  "code": "invalid-security-issue",
                  "msg": "Error: issue \\"CVE-12\\" is not recognized.\n\nCVEs should follow the pattern CVE-yyyy-nnn.\n\nUSNs should follow the pattern USN-nnnn."
                },
                "expected_status": "error",
                "plan": [],
                "title": "CVE-12",
                "warnings": []
              }
            ],
            "expected_status": "error"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-123455", "USN-12"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "error",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {},
                  "affected_packages": null,
                  "description": null,
                  "error": {
                    "code": "invalid-security-issue",
                    "msg": "Error: issue \\"USN-123455\\" is not recognized.\n\nCVEs should follow the pattern CVE-yyyy-nnn.\n\nUSNs should follow the pattern USN-nnnn."
                  },
                  "expected_status": "error",
                  "plan": [],
                  "title": "USN-123455",
                  "warnings": []
                }
              },
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {},
                  "affected_packages": null,
                  "description": null,
                  "error": {
                    "code": "invalid-security-issue",
                    "msg": "Error: issue \\"USN-12\\" is not recognized.\n\nCVEs should follow the pattern CVE-yyyy-nnn.\n\nUSNs should follow the pattern USN-nnnn."
                  },
                  "expected_status": "error",
                  "plan": [],
                  "title": "USN-12",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """

    Examples: ubuntu release details
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "krb5"
                ],
                "description": "Kerberos vulnerability",
                "error": null,
                "expected_status": "fixed",
                "plan": [
                  {
                    "data": {
                      "pocket": "standard-updates",
                      "source_packages": [
                        "krb5"
                      ],
                      "status": "cve-already-fixed"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2020-28196",
                "warnings": []
              }
            ],
            "expected_status": "fixed"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2022-24959"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [],
                "description": "Linux kernel vulnerabilities",
                "error": null,
                "expected_status": "not-affected",
                "plan": [
                  {
                    "data": {
                      "status": "system-not-affected"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2022-24959",
                "warnings": []
              }
            ],
            "expected_status": "not-affected"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2022-24959"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "krb5"
                ],
                "description": "Kerberos vulnerability",
                "error": null,
                "expected_status": "fixed",
                "plan": [
                  {
                    "data": {
                      "pocket": "standard-updates",
                      "source_packages": [
                        "krb5"
                      ],
                      "status": "cve-already-fixed"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2020-28196",
                "warnings": []
              },
              {
                "additional_data": {},
                "affected_packages": [],
                "description": "Linux kernel vulnerabilities",
                "error": null,
                "expected_status": "not-affected",
                "plan": [
                  {
                    "data": {
                      "status": "system-not-affected"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2022-24959",
                "warnings": []
              }
            ],
            "expected_status": "fixed"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I apt install `libawl-php=0.60-1`
    And I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-4539-1"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2020-11728"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "awl"
                  ],
                  "description": "AWL vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "binary_packages": [
                          "libawl-php"
                        ],
                        "pocket": "standard-updates",
                        "source_packages": [
                          "awl"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 1
                    }
                  ],
                  "title": "USN-4539-1",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I apt install `rsync=3.1.3-8 zlib1g=1:1.2.11.dfsg-2ubuntu1`
    And I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-5573-1"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-37434"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "zlib vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5570-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-37434"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [
                      "zlib"
                    ],
                    "description": "zlib vulnerability",
                    "error": null,
                    "expected_status": "fixed",
                    "plan": [
                      {
                        "data": {
                          "binary_packages": [
                            "zlib1g"
                          ],
                          "pocket": "standard-updates",
                          "source_packages": [
                            "zlib"
                          ]
                        },
                        "operation": "apt-upgrade",
                        "order": 1
                      }
                    ],
                    "title": "USN-5570-2",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2018-25032",
                        "CVE-2016-9840",
                        "CVE-2022-37434",
                        "CVE-2016-9841"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [
                      "klibc"
                    ],
                    "description": "klibc vulnerabilities",
                    "error": null,
                    "expected_status": "fixed",
                    "plan": [
                      {
                        "data": {
                          "pocket": "standard-updates",
                          "source_packages": [
                            "klibc"
                          ],
                          "status": "cve-already-fixed"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6736-1",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2022-37434"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "rsync"
                  ],
                  "description": "rsync vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "binary_packages": [
                          "rsync"
                        ],
                        "pocket": "standard-updates",
                        "source_packages": [
                          "rsync"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 1
                    }
                  ],
                  "title": "USN-5573-1",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-4539-1", "USN-5573-1"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2020-11728"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "awl"
                  ],
                  "description": "AWL vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "binary_packages": [
                          "libawl-php"
                        ],
                        "pocket": "standard-updates",
                        "source_packages": [
                          "awl"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 1
                    }
                  ],
                  "title": "USN-4539-1",
                  "warnings": []
                }
              },
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-37434"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "zlib vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5570-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-37434"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [
                      "zlib"
                    ],
                    "description": "zlib vulnerability",
                    "error": null,
                    "expected_status": "fixed",
                    "plan": [
                      {
                        "data": {
                          "binary_packages": [
                            "zlib1g"
                          ],
                          "pocket": "standard-updates",
                          "source_packages": [
                            "zlib"
                          ]
                        },
                        "operation": "apt-upgrade",
                        "order": 1
                      }
                    ],
                    "title": "USN-5570-2",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2018-25032",
                        "CVE-2016-9840",
                        "CVE-2022-37434",
                        "CVE-2016-9841"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [
                      "klibc"
                    ],
                    "description": "klibc vulnerabilities",
                    "error": null,
                    "expected_status": "fixed",
                    "plan": [
                      {
                        "data": {
                          "pocket": "standard-updates",
                          "source_packages": [
                            "klibc"
                          ],
                          "status": "cve-already-fixed"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6736-1",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2022-37434"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "rsync"
                  ],
                  "description": "rsync vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "binary_packages": [
                          "rsync"
                        ],
                        "pocket": "standard-updates",
                        "source_packages": [
                          "rsync"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 1
                    }
                  ],
                  "title": "USN-5573-1",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """

    Examples: ubuntu release details
      | release | machine_type  |
      | focal   | lxd-container |

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-15180"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [],
                "description": "MariaDB vulnerabilities",
                "error": null,
                "expected_status": "not-affected",
                "plan": [
                  {
                    "data": {
                      "status": "system-not-affected"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2020-15180",
                "warnings": []
              }
            ],
            "expected_status": "not-affected"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "krb5"
                ],
                "description": "Kerberos vulnerability",
                "error": null,
                "expected_status": "fixed",
                "plan": [
                  {
                    "data": {
                      "pocket": "standard-updates",
                      "source_packages": [
                        "krb5"
                      ],
                      "status": "cve-already-fixed"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2020-28196",
                "warnings": []
              }
            ],
            "expected_status": "fixed"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I apt install `expat=2.1.0-7 swish-e matanza ghostscript`
    And I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2017-9233"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "expat",
                  "matanza",
                  "swish-e"
                ],
                "description": "Expat vulnerability",
                "error": null,
                "expected_status": "still-affected",
                "plan": [
                  {
                    "data": {
                      "binary_packages": [
                        "expat"
                      ],
                      "pocket": "standard-updates",
                      "source_packages": [
                        "expat"
                      ]
                    },
                    "operation": "apt-upgrade",
                    "order": 2
                  }
                ],
                "title": "CVE-2017-9233",
                "warnings": [
                  {
                    "data": {
                      "source_packages": [
                        "matanza",
                        "swish-e"
                      ],
                      "status": "needs-triage"
                    },
                    "order": 1,
                    "warning_type": "security-issue-not-fixed"
                  }
                ]
              }
            ],
            "expected_status": "still-affected"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196", "CVE-2020-15180", "CVE-2017-9233"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "krb5"
                ],
                "description": "Kerberos vulnerability",
                "error": null,
                "expected_status": "fixed",
                "plan": [
                  {
                    "data": {
                      "pocket": "standard-updates",
                      "source_packages": [
                        "krb5"
                      ],
                      "status": "cve-already-fixed"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2020-28196",
                "warnings": []
              },
              {
                "additional_data": {},
                "affected_packages": [],
                "description": "MariaDB vulnerabilities",
                "error": null,
                "expected_status": "not-affected",
                "plan": [
                  {
                    "data": {
                      "status": "system-not-affected"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2020-15180",
                "warnings": []
              },
              {
                "additional_data": {},
                "affected_packages": [
                  "expat",
                  "matanza",
                  "swish-e"
                ],
                "description": "Expat vulnerability",
                "error": null,
                "expected_status": "still-affected",
                "plan": [
                  {
                    "data": {
                      "binary_packages": [
                        "expat"
                      ],
                      "pocket": "standard-updates",
                      "source_packages": [
                        "expat"
                      ]
                    },
                    "operation": "apt-upgrade",
                    "order": 2
                  }
                ],
                "title": "CVE-2017-9233",
                "warnings": [
                  {
                    "data": {
                      "source_packages": [
                        "matanza",
                        "swish-e"
                      ],
                      "status": "needs-triage"
                    },
                    "order": 1,
                    "warning_type": "security-issue-not-fixed"
                  }
                ]
              }
            ],
            "expected_status": "still-affected"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I apt install `libawl-php`
    And I reboot the machine
    And I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-4539-1"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "not-affected",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2020-11728"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [],
                  "description": "AWL vulnerability",
                  "error": null,
                  "expected_status": "not-affected",
                  "plan": [
                    {
                      "data": {
                        "status": "system-not-affected"
                      },
                      "operation": "no-op",
                      "order": 1
                    }
                  ],
                  "title": "USN-4539-1",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-5079-2"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2021-22947",
                        "CVE-2021-22945",
                        "CVE-2021-22946"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "curl vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5079-1",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2021-22946",
                      "CVE-2021-22947"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "curl"
                  ],
                  "description": "curl vulnerabilities",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "reason": "required-pro-service",
                        "required_service": "esm-infra",
                        "source_packages": [
                          "curl"
                        ]
                      },
                      "operation": "attach",
                      "order": 1
                    },
                    {
                      "data": {
                        "service": "esm-infra",
                        "source_packages": [
                          "curl"
                        ]
                      },
                      "operation": "enable",
                      "order": 2
                    },
                    {
                      "data": {
                        "binary_packages": [
                          "curl",
                          "libcurl3-gnutls"
                        ],
                        "pocket": "esm-infra",
                        "source_packages": [
                          "curl"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 3
                    }
                  ],
                  "title": "USN-5079-2",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-5051-2"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2021-3711",
                        "CVE-2021-3712"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "OpenSSL vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5051-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2021-3712"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "OpenSSL vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5051-3",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2019-11098",
                        "CVE-2021-3712",
                        "CVE-2021-23840",
                        "CVE-2021-38575"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "EDK II vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5088-1",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2021-3712"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "openssl"
                  ],
                  "description": "OpenSSL vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "reason": "required-pro-service",
                        "required_service": "esm-infra",
                        "source_packages": [
                          "openssl"
                        ]
                      },
                      "operation": "attach",
                      "order": 1
                    },
                    {
                      "data": {
                        "service": "esm-infra",
                        "source_packages": [
                          "openssl"
                        ]
                      },
                      "operation": "enable",
                      "order": 2
                    },
                    {
                      "data": {
                        "binary_packages": [
                          "libssl1.0.0",
                          "openssl"
                        ],
                        "pocket": "esm-infra",
                        "source_packages": [
                          "openssl"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 3
                    }
                  ],
                  "title": "USN-5051-2",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-5378-4"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-1271"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Gzip vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5378-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-1271"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "XZ Utils vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5378-2",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-1271"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [
                      "xz-utils"
                    ],
                    "description": "XZ Utils vulnerability",
                    "error": null,
                    "expected_status": "fixed",
                    "plan": [
                      {
                        "data": {
                          "reason": "required-pro-service",
                          "required_service": "esm-infra",
                          "source_packages": [
                            "xz-utils"
                          ]
                        },
                        "operation": "attach",
                        "order": 1
                      },
                      {
                        "data": {
                          "service": "esm-infra",
                          "source_packages": [
                            "xz-utils"
                          ]
                        },
                        "operation": "enable",
                        "order": 2
                      },
                      {
                        "data": {
                          "binary_packages": [
                            "liblzma5",
                            "xz-utils"
                          ],
                          "pocket": "esm-infra",
                          "source_packages": [
                            "xz-utils"
                          ]
                        },
                        "operation": "apt-upgrade",
                        "order": 3
                      }
                    ],
                    "title": "USN-5378-3",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2022-1271"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "gzip"
                  ],
                  "description": "Gzip vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "reason": "required-pro-service",
                        "required_service": "esm-infra",
                        "source_packages": [
                          "gzip"
                        ]
                      },
                      "operation": "attach",
                      "order": 1
                    },
                    {
                      "data": {
                        "service": "esm-infra",
                        "source_packages": [
                          "gzip"
                        ]
                      },
                      "operation": "enable",
                      "order": 2
                    },
                    {
                      "data": {
                        "binary_packages": [
                          "gzip"
                        ],
                        "pocket": "esm-infra",
                        "source_packages": [
                          "gzip"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 3
                    }
                  ],
                  "title": "USN-5378-4",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-5051-2", "USN-5378-4"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2021-3711",
                        "CVE-2021-3712"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "OpenSSL vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5051-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2021-3712"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "OpenSSL vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5051-3",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2019-11098",
                        "CVE-2021-3712",
                        "CVE-2021-23840",
                        "CVE-2021-38575"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "EDK II vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5088-1",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2021-3712"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "openssl"
                  ],
                  "description": "OpenSSL vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "reason": "required-pro-service",
                        "required_service": "esm-infra",
                        "source_packages": [
                          "openssl"
                        ]
                      },
                      "operation": "attach",
                      "order": 1
                    },
                    {
                      "data": {
                        "service": "esm-infra",
                        "source_packages": [
                          "openssl"
                        ]
                      },
                      "operation": "enable",
                      "order": 2
                    },
                    {
                      "data": {
                        "binary_packages": [
                          "libssl1.0.0",
                          "openssl"
                        ],
                        "pocket": "esm-infra",
                        "source_packages": [
                          "openssl"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 3
                    }
                  ],
                  "title": "USN-5051-2",
                  "warnings": []
                }
              },
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-1271"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Gzip vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5378-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-1271"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "XZ Utils vulnerability",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-5378-2",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2022-1271"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [
                      "xz-utils"
                    ],
                    "description": "XZ Utils vulnerability",
                    "error": null,
                    "expected_status": "fixed",
                    "plan": [
                      {
                        "data": {
                          "reason": "required-pro-service",
                          "required_service": "esm-infra",
                          "source_packages": [
                            "xz-utils"
                          ]
                        },
                        "operation": "attach",
                        "order": 1
                      },
                      {
                        "data": {
                          "service": "esm-infra",
                          "source_packages": [
                            "xz-utils"
                          ]
                        },
                        "operation": "enable",
                        "order": 2
                      },
                      {
                        "data": {
                          "binary_packages": [
                            "liblzma5",
                            "xz-utils"
                          ],
                          "pocket": "esm-infra",
                          "source_packages": [
                            "xz-utils"
                          ]
                        },
                        "operation": "apt-upgrade",
                        "order": 3
                      }
                    ],
                    "title": "USN-5378-3",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2022-1271"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "gzip"
                  ],
                  "description": "Gzip vulnerability",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "reason": "required-pro-service",
                        "required_service": "esm-infra",
                        "source_packages": [
                          "gzip"
                        ]
                      },
                      "operation": "attach",
                      "order": 1
                    },
                    {
                      "data": {
                        "service": "esm-infra",
                        "source_packages": [
                          "gzip"
                        ]
                      },
                      "operation": "enable",
                      "order": 2
                    },
                    {
                      "data": {
                        "binary_packages": [
                          "gzip"
                        ],
                        "pocket": "esm-infra",
                        "source_packages": [
                          "gzip"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 3
                    }
                  ],
                  "title": "USN-5378-4",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `sed -i "/xenial-updates/d" /etc/apt/sources.list` with sudo
    And I run `sed -i "/xenial-security/d" /etc/apt/sources.list` with sudo
    And I apt update
    And I apt install `squid`
    And I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-25097"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "squid3"
                ],
                "description": "Squid vulnerabilities",
                "error": null,
                "expected_status": "still-affected",
                "plan": [
                  {
                    "data": {
                      "binary_packages": [],
                      "pocket": "standard-updates",
                      "source_packages": [
                        "squid3"
                      ]
                    },
                    "operation": "apt-upgrade",
                    "order": 3
                  }
                ],
                "title": "CVE-2020-25097",
                "warnings": [
                  {
                    "data": {
                      "binary_package": "squid",
                      "binary_package_version": ".*",
                      "pocket": "standard-updates",
                      "related_source_packages": [
                        "squid3"
                      ],
                      "source_package": "squid3"
                    },
                    "order": 1,
                    "warning_type": "package-cannot-be-installed"
                  },
                  {
                    "data": {
                      "binary_package": "squid-common",
                      "binary_package_version": ".*",
                      "pocket": "standard-updates",
                      "related_source_packages": [
                        "squid3"
                      ],
                      "source_package": "squid3"
                    },
                    "order": 2,
                    "warning_type": "package-cannot-be-installed"
                  }
                ]
              }
            ],
            "expected_status": "still-affected"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """

    Examples: ubuntu release details
      | release | machine_type  |
      | xenial  | lxd-container |

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2020-28196"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "krb5"
                ],
                "description": "Kerberos vulnerability",
                "error": null,
                "expected_status": "fixed",
                "plan": [
                  {
                    "data": {
                      "pocket": "standard-updates",
                      "source_packages": [
                        "krb5"
                      ],
                      "status": "cve-already-fixed"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2020-28196",
                "warnings": []
              }
            ],
            "expected_status": "fixed"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I apt install `xterm=330-1ubuntu2`
    And I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2021-27135"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [
                  "xterm"
                ],
                "description": "xterm vulnerability",
                "error": null,
                "expected_status": "fixed",
                "plan": [
                  {
                    "data": {
                      "binary_packages": [
                        "xterm"
                      ],
                      "pocket": "standard-updates",
                      "source_packages": [
                        "xterm"
                      ]
                    },
                    "operation": "apt-upgrade",
                    "order": 1
                  }
                ],
                "title": "CVE-2021-27135",
                "warnings": []
              }
            ],
            "expected_status": "fixed"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """
    When I apt install `libawl-php`
    And I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-4539-1"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "not-affected",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2020-11728"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [],
                  "description": "AWL vulnerability",
                  "error": null,
                  "expected_status": "not-affected",
                  "plan": [
                    {
                      "data": {
                        "status": "system-not-affected"
                      },
                      "operation": "no-op",
                      "order": 1
                    }
                  ],
                  "title": "USN-4539-1",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I apt install `libbz2-1.0=1.0.6-8.1 bzip2=1.0.6-8.1`
    And I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-4038-3"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [],
                    "associated_launchpad_bugs": [
                      "https://launchpad.net/bugs/1834494"
                    ]
                  },
                  "affected_packages": [
                    "bzip2"
                  ],
                  "description": "bzip2 regression",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "binary_packages": [
                          "bzip2",
                          "libbz2-1.0"
                        ],
                        "pocket": "standard-updates",
                        "source_packages": [
                          "bzip2"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 1
                    }
                  ],
                  "title": "USN-4038-3",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-6130-1"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "not-affected",
            "usns": [
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-1076",
                        "CVE-2023-1118",
                        "CVE-2023-25012",
                        "CVE-2023-1855",
                        "CVE-2023-1990",
                        "CVE-2023-28866",
                        "CVE-2023-1998",
                        "CVE-2023-1077",
                        "CVE-2023-1583",
                        "CVE-2023-1670",
                        "CVE-2023-1032",
                        "CVE-2023-1079",
                        "CVE-2023-30456",
                        "CVE-2023-28466",
                        "CVE-2023-1989",
                        "CVE-2023-1829",
                        "CVE-2022-4269"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (OEM) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6033-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-32233",
                        "CVE-2023-2612"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (OEM) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6122-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-30456",
                        "CVE-2023-2612",
                        "CVE-2023-1670",
                        "CVE-2023-26606",
                        "CVE-2023-32233"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (OEM) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6123-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-30456",
                        "CVE-2023-32233",
                        "CVE-2023-2612",
                        "CVE-2022-4139",
                        "CVE-2022-3586",
                        "CVE-2023-1670"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (OEM) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6124-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-32233",
                        "CVE-2023-1380",
                        "CVE-2023-2612",
                        "CVE-2023-31436",
                        "CVE-2023-30456"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6127-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-30456",
                        "CVE-2023-1380",
                        "CVE-2023-32233",
                        "CVE-2023-2612",
                        "CVE-2023-31436"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6131-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-0459",
                        "CVE-2023-30456",
                        "CVE-2023-1380",
                        "CVE-2023-1075",
                        "CVE-2023-2162",
                        "CVE-2023-32233",
                        "CVE-2023-2612",
                        "CVE-2022-3707",
                        "CVE-2023-1118",
                        "CVE-2023-1513",
                        "CVE-2023-32269",
                        "CVE-2023-31436",
                        "CVE-2023-1078"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6132-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-32233",
                        "CVE-2023-1380",
                        "CVE-2023-2612",
                        "CVE-2023-31436",
                        "CVE-2023-30456"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (Azure CVM) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6135-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-32233",
                        "CVE-2023-28328",
                        "CVE-2023-1073",
                        "CVE-2023-30456",
                        "CVE-2023-1380",
                        "CVE-2023-31436"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6149-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-30456",
                        "CVE-2023-1380",
                        "CVE-2023-32233",
                        "CVE-2023-2612",
                        "CVE-2023-31436"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6150-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-31436",
                        "CVE-2023-2612",
                        "CVE-2023-30456",
                        "CVE-2023-1380",
                        "CVE-2023-32233"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (Intel IoTG) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6162-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-32254",
                        "CVE-2023-2002",
                        "CVE-2023-2156",
                        "CVE-2023-32250",
                        "CVE-2023-2269",
                        "CVE-2023-1380",
                        "CVE-2023-31436"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (OEM) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6173-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-33203",
                        "CVE-2023-1859",
                        "CVE-2023-1855",
                        "CVE-2023-33288",
                        "CVE-2023-2194",
                        "CVE-2023-30456",
                        "CVE-2023-32233",
                        "CVE-2023-2235",
                        "CVE-2023-2612",
                        "CVE-2023-28466",
                        "CVE-2023-1380",
                        "CVE-2023-1611",
                        "CVE-2023-1990",
                        "CVE-2023-31436",
                        "CVE-2023-1989",
                        "CVE-2023-1583",
                        "CVE-2023-28866",
                        "CVE-2023-30772",
                        "CVE-2023-1670",
                        "CVE-2022-4269"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6175-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-33203",
                        "CVE-2023-1859",
                        "CVE-2023-1855",
                        "CVE-2023-33288",
                        "CVE-2023-2194",
                        "CVE-2023-30456",
                        "CVE-2023-32233",
                        "CVE-2023-2235",
                        "CVE-2023-2612",
                        "CVE-2023-28466",
                        "CVE-2023-1380",
                        "CVE-2023-1611",
                        "CVE-2023-1990",
                        "CVE-2023-31436",
                        "CVE-2023-1989",
                        "CVE-2023-1583",
                        "CVE-2023-28866",
                        "CVE-2023-30772",
                        "CVE-2023-1670",
                        "CVE-2022-4269"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6186-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-1380",
                        "CVE-2023-32233",
                        "CVE-2022-4129",
                        "CVE-2023-2162",
                        "CVE-2023-26545",
                        "CVE-2022-3108",
                        "CVE-2023-1670",
                        "CVE-2023-1998",
                        "CVE-2022-3707",
                        "CVE-2023-1281",
                        "CVE-2023-1118",
                        "CVE-2023-30456",
                        "CVE-2023-0459",
                        "CVE-2023-2985",
                        "CVE-2023-1074",
                        "CVE-2023-2612",
                        "CVE-2023-1859",
                        "CVE-2023-32269",
                        "CVE-2023-1076",
                        "CVE-2022-3903",
                        "CVE-2023-1073",
                        "CVE-2023-1079",
                        "CVE-2023-0458",
                        "CVE-2023-1829",
                        "CVE-2023-1078",
                        "CVE-2023-3161",
                        "CVE-2023-25012",
                        "CVE-2023-1075",
                        "CVE-2023-1513",
                        "CVE-2023-1077",
                        "CVE-2023-31436"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (Xilinx ZynqMP) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6222-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-2162",
                        "CVE-2022-3707",
                        "CVE-2023-1078",
                        "CVE-2022-4129",
                        "CVE-2023-0459",
                        "CVE-2023-1859",
                        "CVE-2023-1077",
                        "CVE-2023-1079",
                        "CVE-2023-32269",
                        "CVE-2023-0458",
                        "CVE-2022-3903",
                        "CVE-2023-3161",
                        "CVE-2023-25012",
                        "CVE-2023-30456",
                        "CVE-2023-35788",
                        "CVE-2023-2612",
                        "CVE-2023-1829",
                        "CVE-2023-32233",
                        "CVE-2023-31436",
                        "CVE-2023-1380",
                        "CVE-2023-26545",
                        "CVE-2023-1075",
                        "CVE-2023-1998",
                        "CVE-2022-3108",
                        "CVE-2023-1513",
                        "CVE-2023-1074",
                        "CVE-2023-1073",
                        "CVE-2023-1281",
                        "CVE-2023-1670",
                        "CVE-2023-2985",
                        "CVE-2023-1118",
                        "CVE-2023-1076"
                      ],
                      "associated_launchpad_bugs": [
                        "https://launchpad.net/bugs/2023220",
                        "https://launchpad.net/bugs/2023577"
                      ]
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (IoT) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6256-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-3141",
                        "CVE-2023-40283",
                        "CVE-2023-28328",
                        "CVE-2023-3220",
                        "CVE-2023-1206",
                        "CVE-2023-1075",
                        "CVE-2023-4273",
                        "CVE-2023-4015",
                        "CVE-2022-27672",
                        "CVE-2023-1076",
                        "CVE-2023-28466",
                        "CVE-2023-3609",
                        "CVE-2023-4128",
                        "CVE-2023-2898",
                        "CVE-2023-3090",
                        "CVE-2023-2235",
                        "CVE-2023-2002",
                        "CVE-2023-32269",
                        "CVE-2023-3863",
                        "CVE-2023-31436",
                        "CVE-2023-2163",
                        "CVE-2023-3777",
                        "CVE-2023-3390",
                        "CVE-2023-3611",
                        "CVE-2023-3776",
                        "CVE-2023-0458",
                        "CVE-2023-4004",
                        "CVE-2023-4194",
                        "CVE-2022-4269",
                        "CVE-2023-20593",
                        "CVE-2023-1611",
                        "CVE-2023-2269",
                        "CVE-2023-1380",
                        "CVE-2023-3995",
                        "CVE-2023-2162",
                        "CVE-2023-3610",
                        "CVE-2023-4569"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel (OEM) vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6385-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2023-42755",
                        "CVE-2023-1380",
                        "CVE-2023-42752",
                        "CVE-2023-35001",
                        "CVE-2023-1206",
                        "CVE-2023-4623",
                        "CVE-2023-31436"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6460-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2024-24855",
                        "CVE-2023-30456",
                        "CVE-2023-4921"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "Linux kernel vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-6699-1",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2023-30456",
                      "CVE-2023-1380",
                      "CVE-2023-32233",
                      "CVE-2023-31436"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [],
                  "description": "Linux kernel vulnerabilities",
                  "error": null,
                  "expected_status": "not-affected",
                  "plan": [
                    {
                      "data": {
                        "status": "system-not-affected"
                      },
                      "operation": "no-op",
                      "order": 1
                    }
                  ],
                  "title": "USN-6130-1",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """
    When I run `pro api u.pro.security.fix.usn.plan.v1 --data '{"usns": ["USN-4539-1", "USN-4038-1"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `usn_fix_plan` schema
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "usns_data": {
            "expected_status": "fixed",
            "usns": [
              {
                "related_usns_plan": [],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2020-11728"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [],
                  "description": "AWL vulnerability",
                  "error": null,
                  "expected_status": "not-affected",
                  "plan": [
                    {
                      "data": {
                        "status": "system-not-affected"
                      },
                      "operation": "no-op",
                      "order": 1
                    }
                  ],
                  "title": "USN-4539-1",
                  "warnings": []
                }
              },
              {
                "related_usns_plan": [
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2016-3189",
                        "CVE-2019-12900"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "bzip2 vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-4038-2",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2019-12625",
                        "CVE-2019-12900"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "ClamAV vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-4146-1",
                    "warnings": []
                  },
                  {
                    "additional_data": {
                      "associated_cves": [
                        "CVE-2019-12625",
                        "CVE-2019-12900"
                      ],
                      "associated_launchpad_bugs": []
                    },
                    "affected_packages": [],
                    "description": "ClamAV vulnerabilities",
                    "error": null,
                    "expected_status": "not-affected",
                    "plan": [
                      {
                        "data": {
                          "status": "system-not-affected"
                        },
                        "operation": "no-op",
                        "order": 1
                      }
                    ],
                    "title": "USN-4146-2",
                    "warnings": []
                  }
                ],
                "target_usn_plan": {
                  "additional_data": {
                    "associated_cves": [
                      "CVE-2016-3189",
                      "CVE-2019-12900"
                    ],
                    "associated_launchpad_bugs": []
                  },
                  "affected_packages": [
                    "bzip2"
                  ],
                  "description": "bzip2 vulnerabilities",
                  "error": null,
                  "expected_status": "fixed",
                  "plan": [
                    {
                      "data": {
                        "binary_packages": [
                          "bzip2",
                          "libbz2-1.0"
                        ],
                        "pocket": "standard-updates",
                        "source_packages": [
                          "bzip2"
                        ]
                      },
                      "operation": "apt-upgrade",
                      "order": 1
                    }
                  ],
                  "title": "USN-4038-1",
                  "warnings": []
                }
              }
            ]
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "USNFixPlan"
      }
      """

    Examples: ubuntu release details
      | release | machine_type  |
      | bionic  | lxd-container |

  Scenario Outline: Fix command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.security.fix.cve.plan.v1 --data '{"cves": ["CVE-2022-40982"]}'` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `cve_fix_plan` schema
    And API data field output matches regexp:
      """
      {
        "attributes": {
          "cves_data": {
            "cves": [
              {
                "additional_data": {},
                "affected_packages": [],
                "description": "Linux kernel (BlueField) vulnerabilities",
                "error": null,
                "expected_status": "not-affected",
                "plan": [
                  {
                    "data": {
                      "status": "system-not-affected"
                    },
                    "operation": "no-op",
                    "order": 1
                  }
                ],
                "title": "CVE-2022-40982",
                "warnings": []
              }
            ],
            "expected_status": "not-affected"
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "CVEFixPlan"
      }
      """

    Examples: ubuntu release details
      | release | machine_type |
      | mantic  | lxd-vm       |

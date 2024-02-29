Feature: Client behaviour for the API endpoints

  Scenario Outline: all API endpoints can be imported individually
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `python3 -c "from uaclient.api.u.pro.attach.auto.configure_retry_service.v1 import configure_retry_service"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import full_auto_attach"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.attach.auto.should_auto_attach.v1 import should_auto_attach"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.attach.magic.initiate.v1 import initiate"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.attach.magic.revoke.v1 import revoke"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.attach.magic.wait.v1 import wait"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.packages.summary.v1 import summary"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.packages.updates.v1 import updates"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.security.fix.cve.execute.v1 import execute"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.security.fix.usn.execute.v1 import execute"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.security.fix.cve.plan.v1 import plan"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.security.fix.usn.plan.v1 import plan"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.security.status.livepatch_cves.v1 import livepatch_cves"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.security.status.reboot_required.v1 import reboot_required"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.services.dependencies.v1 import dependencies"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.status.enabled_services.v1 import enabled_services"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.status.is_attached.v1 import is_attached"` as non-root
    When I run `python3 -c "from uaclient.api.u.pro.version.v1 import version"` as non-root
    When I run `python3 -c "from uaclient.api.u.security.package_manifest.v1 import package_manifest"` as non-root
    When I run `python3 -c "from uaclient.api.u.unattended_upgrades.status.v1 import status"` as non-root
    When I run `python3 -c "from uaclient.api.u.apt_news.current_news.v1 import current_news"` as non-root

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |

  Scenario Outline: API invalid endpoint or args
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro api invalid.endpoint` `with sudo` exits `1`
    Then API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "meta": {
            "environment_vars": []
          }
        },
        "errors": [
          {
            "code": "api-invalid-endpoint",
            "meta": {
              "endpoint": "invalid\.endpoint"
            },
            "title": "'invalid\.endpoint' is not a valid endpoint"
          }
        ],
        "result": "failure",
        "version": ".*",
        "warnings": []
      }
      """
    When I verify that running `pro api u.pro.version.v1 --args extra=arg` `with sudo` exits `1`
    Then API errors field output matches regexp:
      """
      [
        {
          "code": "api-no-argument-for-endpoint",
          "meta": {
            "endpoint": "u.pro.version.v1"
          },
          "title": "u.pro.version.v1 accepts no arguments"
        }
      ]
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |

  Scenario Outline: Basic endpoints
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.version.v1` with sudo
    Then API full output matches regexp:
      """
      {
        "_schema_version": "v1",
        "data": {
          "attributes": {
            "installed_version": ".*"
          },
          "meta": {
            "environment_vars": []
          },
          "type": "Version"
        },
        "errors": [],
        "result": "success",
        "version": ".*",
        "warnings": []
      }
      """
    When I run `UA_LOG_FILE=/tmp/some_file OTHER_ENVVAR=not_there pro api u.pro.version.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "installed_version": ".*"
        },
        "meta": {
          "environment_vars": [
            {
              "name": "UA_LOG_FILE",
              "value": "/tmp/some_file"
            }
          ]
        },
        "type": "Version"
      }
      """
    When I run `pro api u.pro.attach.auto.should_auto_attach.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "should_auto_attach": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "ShouldAutoAttach"
      }
      """
    When I run `pro api u.pro.status.is_attached.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "contract_remaining_days": 0,
          "contract_status": null,
          "is_attached": false,
          "is_attached_and_contract_valid": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "IsAttached"
      }
      """
    When I run `pro api u.pro.status.enabled_services.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "enabled_services": []
        },
        "meta": {
          "environment_vars": []
        },
        "type": "EnabledServices"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |

  @uses.config.contract_token
  Scenario Outline: u.pro.status.is_attached.v1
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.status.is_attached.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "contract_remaining_days": 0,
          "contract_status": null,
          "is_attached": false,
          "is_attached_and_contract_valid": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "IsAttached"
      }
      """
    When I attach `contract_token` with sudo
    And I run `pro api u.pro.status.is_attached.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "contract_remaining_days": \d+,
          "contract_status": "active",
          "is_attached": true,
          "is_attached_and_contract_valid": true
        },
        "meta": {
          "environment_vars": []
        },
        "type": "IsAttached"
      }
      """
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          effectiveTo: $behave_var{today +2}
      """
    And I run `ua api u.pro.status.is_attached.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "contract_remaining_days": 2,
          "contract_status": "active-soon-to-expire",
          "is_attached": true,
          "is_attached_and_contract_valid": true
        },
        "meta": {
          "environment_vars": []
        },
        "type": "IsAttached"
      }
      """
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          effectiveTo: $behave_var{today -2}
      """
    And I run `pro api u.pro.status.is_attached.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "contract_remaining_days": -2,
          "contract_status": "grace-period",
          "is_attached": true,
          "is_attached_and_contract_valid": true
        },
        "meta": {
          "environment_vars": []
        },
        "type": "IsAttached"
      }
      """
    When I set the machine token overlay to the following yaml
      """
      machineTokenInfo:
        contractInfo:
          effectiveTo: $behave_var{today -50}
      """
    And I run `pro api u.pro.status.is_attached.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "contract_remaining_days": -50,
          "contract_status": "expired",
          "is_attached": true,
          "is_attached_and_contract_valid": false
        },
        "meta": {
          "environment_vars": []
        },
        "type": "IsAttached"
      }
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |

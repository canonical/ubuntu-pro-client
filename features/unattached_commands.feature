Feature: Command behaviour when unattached

  Scenario Outline: Unattached auto-attach does nothing in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # Validate systemd unit/timer syntax
    When I run `systemd-analyze verify /lib/systemd/system/ua-timer.timer` with sudo
    Then stderr does not match regexp:
      """
      .*\/lib\/systemd/system\/ua.*
      """
    When I verify that running `pro auto-attach` `as non-root` exits `1`
    Then stderr matches regexp:
      """
      This command must be run as root \(try using sudo\).
      """
    When I run `pro auto-attach` with sudo
    Then stderr matches regexp:
      """
      Auto-attach image support is not available on lxd
      See: https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/explanations/what_are_ubuntu_pro_cloud_instances.html
      """

    Examples: ubuntu release
      | release | machine_type  |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | xenial  | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: Unattached commands that requires enabled user in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro <command>` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro <command>` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      This machine is not attached to an Ubuntu Pro subscription.
      See https://ubuntu.com/pro
      """

    Examples: pro commands
      | release | machine_type  | command |
      | bionic  | lxd-container | detach  |
      | bionic  | lxd-container | refresh |
      | bionic  | wsl           | detach  |
      | bionic  | wsl           | refresh |
      | focal   | lxd-container | detach  |
      | focal   | lxd-container | refresh |
      | focal   | wsl           | detach  |
      | focal   | wsl           | refresh |
      | xenial  | lxd-container | detach  |
      | xenial  | lxd-container | refresh |
      | jammy   | lxd-container | detach  |
      | jammy   | lxd-container | refresh |
      | jammy   | wsl           | detach  |
      | jammy   | wsl           | refresh |
      | mantic  | lxd-container | detach  |
      | mantic  | lxd-container | refresh |
      | noble   | lxd-container | detach  |
      | noble   | lxd-container | refresh |

  Scenario Outline: Help command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro help esm-infra` as non-root
    Then I will see the following on stdout:
      """
      Name:
      esm-infra

      Available:
      <infra-available>

      Help:
      Expanded Security Maintenance for Infrastructure provides access to a private
      PPA which includes available high and critical CVE fixes for Ubuntu LTS
      packages in the Ubuntu Main repository between the end of the standard Ubuntu
      LTS security maintenance and its end of life. It is enabled by default with
      Ubuntu Pro. You can find out more about the service at
      https://ubuntu.com/security/esm
      """
    When I run `pro help esm-infra --format json` with sudo
    Then I will see the following on stdout:
      """
      {"name": "esm-infra", "available": "<infra-available>", "help": "Expanded Security Maintenance for Infrastructure provides access to a private\nPPA which includes available high and critical CVE fixes for Ubuntu LTS\npackages in the Ubuntu Main repository between the end of the standard Ubuntu\nLTS security maintenance and its end of life. It is enabled by default with\nUbuntu Pro. You can find out more about the service at\nhttps://ubuntu.com/security/esm"}
      """
    When I verify that running `pro help invalid-service` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      No help available for 'invalid-service'
      """
    When I verify that running `pro --no-command` `with sudo` exits `2`
    Then I will see the following on stderr:
      """
      usage: pro [-h] [--debug] [--version] <command> ...
      pro: error: the following arguments are required: <command>
      """

    Examples: ubuntu release
      | release | machine_type  | infra-available |
      | xenial  | lxd-container | yes             |
      | bionic  | lxd-container | yes             |
      | bionic  | wsl           | yes             |
      | focal   | lxd-container | yes             |
      | focal   | wsl           | yes             |
      | jammy   | lxd-container | yes             |
      | jammy   | wsl           | yes             |
      | mantic  | lxd-container | no              |
      | noble   | lxd-container | yes             |

  Scenario Outline: Unattached enable/disable fails in a ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro <command> esm-infra` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro <command> esm-infra` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot <command> services when unattached - nothing to do.
      To use 'esm-infra' you need an Ubuntu Pro subscription.
      Personal and community subscriptions are available at no charge.
      See https://ubuntu.com/pro
      """
    When I verify that running `pro <command> esm-infra --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"additional_info": {"operation": "<command>", "valid_service": "esm-infra"}, "message": "Cannot <command> services when unattached - nothing to do.\nTo use 'esm-infra' you need an Ubuntu Pro subscription.\nPersonal and community subscriptions are available at no charge.\nSee https://ubuntu.com/pro", "message_code": "valid-service-failure-unattached", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    When I verify that running `pro <command> unknown` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro <command> unknown` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot <command> unknown service 'unknown'.
      """
    When I verify that running `pro <command> unknown --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"additional_info": {"invalid_service": "unknown", "operation": "<command>", "service_msg": ""}, "message": "Cannot <command> unknown service 'unknown'.\n", "message_code": "invalid-service-or-failure", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    When I verify that running `pro <command> esm-infra unknown` `as non-root` exits `1`
    Then I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I verify that running `pro <command> esm-infra unknown` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      Cannot <command> unknown service 'unknown'.

      Cannot <command> services when unattached - nothing to do.
      To use 'esm-infra' you need an Ubuntu Pro subscription.
      Personal and community subscriptions are available at no charge.
      See https://ubuntu.com/pro
      """
    When I verify that running `pro <command> esm-infra unknown --format json --assume-yes` `with sudo` exits `1`
    Then stdout is a json matching the `ua_operation` schema
    And I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"additional_info": {"invalid_service": "unknown", "operation": "<command>", "service_msg": "", "valid_service": "esm-infra"}, "message": "Cannot <command> unknown service 'unknown'.\n\nCannot <command> services when unattached - nothing to do.\nTo use 'esm-infra' you need an Ubuntu Pro subscription.\nPersonal and community subscriptions are available at no charge.\nSee https://ubuntu.com/pro", "message_code": "mixed-services-failure-unattached", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """

    Examples: ubuntu release
      | release | machine_type  | command |
      | xenial  | lxd-container | enable  |
      | xenial  | lxd-container | disable |
      | bionic  | lxd-container | enable  |
      | bionic  | lxd-container | disable |
      | bionic  | wsl           | enable  |
      | bionic  | wsl           | disable |
      | focal   | lxd-container | enable  |
      | focal   | lxd-container | disable |
      | focal   | wsl           | enable  |
      | focal   | wsl           | disable |
      | jammy   | lxd-container | enable  |
      | jammy   | lxd-container | disable |
      | jammy   | wsl           | enable  |
      | jammy   | wsl           | disable |
      | mantic  | lxd-container | enable  |
      | mantic  | lxd-container | disable |
      | noble   | lxd-container | enable  |
      | noble   | lxd-container | disable |

  Scenario Outline: Check for newer versions of the client in an ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    # Make sure we have a fresh, just rebooted, environment
    When I reboot the machine
    Then I verify that no files exist matching `/run/ubuntu-advantage/candidate-version`
    When I run `pro status` with sudo
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    And I verify that files exist matching `/run/ubuntu-advantage/candidate-version`
    # We forge a candidate to see results
    When I delete the file `/run/ubuntu-advantage/candidate-version`
    And I create the file `/run/ubuntu-advantage/candidate-version` with the following
      """
      2:99.9.9
      """
    And I run `pro status` as non-root
    Then stderr matches regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I run `pro status --format json` as non-root
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I run `pro config show` as non-root
    Then stderr matches regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I run `pro api u.pro.version.v1` as non-root
    Then stdout matches regexp
      """
      \"code\": \"new-version-available\"
      """
    When I verify that running `pro api u.pro.version.inexistent` `as non-root` exits `1`
    Then stdout matches regexp
      """
      \"code\": \"new-version-available\"
      """
    When I run `pro api u.pro.version.v1` as non-root
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """
    When I apt update
    # The update will bring a new candidate, which is the current installed version
    And I run `pro status` as non-root
    Then stderr does not match regexp:
      """
      .*\[info\].* A new version is available: 2:99.9.9
      Please run:
          sudo apt install ubuntu-pro-client
      to get the latest bug fixes and new features.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

  # Side effect: this verifies that `ua` still works as a command
  Scenario Outline: Verify autocomplete options
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I prepare the autocomplete test
    And I press tab twice to autocomplete the `ua` command
    Then stdout matches regexp:
      """
      --debug    +auto-attach   +enable   +status\r
      --help     +collect-logs  +fix      +system\r
      --version  +config        +help     +version\r
      api        +detach        +refresh  +\r
      attach     +disable       +security-status
      """
    When I press tab twice to autocomplete the `pro` command
    Then stdout matches regexp:
      """
      --debug    +auto-attach   +enable   +status\r
      --help     +collect-logs  +fix      +system\r
      --version  +config        +help     +version\r
      api        +detach        +refresh  +\r
      attach     +disable       +security-status
      """
    When I press tab twice to autocomplete the `ua enable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """
    When I press tab twice to autocomplete the `pro enable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """
    When I press tab twice to autocomplete the `ua disable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """
    When I press tab twice to autocomplete the `pro disable` command
    Then stdout matches regexp:
      """
      anbox-cloud +esm-infra    +livepatch       +usg\s*
      cc-eal      +fips         +realtime-kernel\s*
      cis         +fips-updates +ros\s*
      esm-apps    +landscape    +ros-updates\s*
      """

    Examples: ubuntu release
      | release | machine_type  |
      # | xenial  | lxd-container | Can't rely on Xenial because of bash sorting things weirdly
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

  Scenario Outline: esm cache failures don't generate errors
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I disable access to esm.ubuntu.com
    And I apt update
    # Wait for the hook to fail
    When I wait `5` seconds
    And I run `systemctl --failed` with sudo
    Then stdout does not match regexp:
      """
      esm-cache\.service
      """
    When I run `journalctl -o cat -u esm-cache.service` with sudo
    Then stdout does not contain substring:
      """
      raise FetchFailedException()
      """
    Then stdout matches regexp:
      """
      "WARNING", "ubuntupro.apt", "fail", \d+, "Failed to fetch ESM Apt Cache item: https://esm.ubuntu.com/apps/ubuntu/dists/<release>-apps-security/InRelease", {}]
      """
    When I run `ls /var/crash/` with sudo
    Then stdout does not contain substring:
      """
      _usr_lib_ubuntu-advantage_esm_cache
      """

    Examples: ubuntu release
      | release | machine_type  |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

  # Duplicating just for xenial so we disable it on GH
  # See GH: #3013
  @no_gh
  Scenario Outline: esm cache failures don't generate errors on xenial
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I disable access to esm.ubuntu.com
    And I apt update
    # Wait for the hook to fail
    When I wait `5` seconds
    And I run `systemctl --failed` with sudo
    Then stdout does not match regexp:
      """
      esm-cache\.service
      """
    When I run `journalctl -o cat -u esm-cache.service` with sudo
    Then stdout does not contain substring:
      """
      raise FetchFailedException()
      """
    Then stdout matches regexp:
      """
      "WARNING", "ubuntupro.apt", "fail", \d+, "Failed to fetch ESM Apt Cache item: https://esm.ubuntu.com/apps/ubuntu/dists/<release>-apps-security/InRelease", {}]
      """
    When I run `ls /var/crash/` with sudo
    Then stdout does not contain substring:
      """
      _usr_lib_ubuntu-advantage_esm_cache
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |

  # Services fail, degraded systemctl, but no crashes.
  Scenario Outline: services fail gracefully when yaml is broken/absent
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `rm -rf /usr/lib/python3/dist-packages/yaml` with sudo
    And I verify that running `pro status` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Couldn't import the YAML module.
      Make sure the 'python3-yaml' package is installed correctly
      and \/usr\/lib\/python3\/dist-packages is in your PYTHONPATH\.
      """
    When I verify that running `python3 /usr/lib/ubuntu-advantage/esm_cache.py` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Couldn't import the YAML module.
      Make sure the 'python3-yaml' package is installed correctly
      and \/usr\/lib\/python3\/dist-packages is in your PYTHONPATH\.
      """
    When I verify that running `systemctl start apt-news.service` `with sudo` exits `1`
    And I verify that running `systemctl start esm-cache.service` `with sudo` exits `1`
    And I run `systemctl --failed` with sudo
    Then stdout matches regexp:
      """
      apt-news.service
      """
    And stdout matches regexp:
      """
      esm-cache.service
      """
    When I apt install `python3-pip`
    And I run `pip3 install pyyaml==3.10 <suffix>` with sudo
    And I run `ls /usr/local/lib/<python_version>/dist-packages/` with sudo
    Then stdout matches regexp:
      """
      yaml
      """
    And I verify that running `pro status` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Error while trying to parse a yaml file using 'yaml' from
      """
    # Test the specific script which triggered LP #2007241
    When I verify that running `python3 /usr/lib/ubuntu-advantage/esm_cache.py` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Error while trying to parse a yaml file using 'yaml' from
      """
    When I verify that running `systemctl start apt-news.service` `with sudo` exits `1`
    And I verify that running `systemctl start esm-cache.service` `with sudo` exits `1`
    And I run `systemctl --failed` with sudo
    Then stdout matches regexp:
      """
      apt-news.service
      """
    And stdout matches regexp:
      """
      esm-cache.service
      """
    When I run `ls /var/crash` with sudo
    Then I will see the following on stdout
      """
      """

    Examples: ubuntu release
      | release | machine_type  | python_version | suffix                  |
      | jammy   | lxd-container | python3.10     |                         |
      # mantic has a BIG error message explaining why this is a clear user error...
      | mantic  | lxd-container | python3.11     | --break-system-packages |

  # noble doesn't even allow --break-system-packages to work
  # | noble   | lxd-container | python3.11     | --break-system-packages |
  Scenario Outline: Warn users not to redirect/pipe human readable output
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run shell command `pro version | cat` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro version > version_out` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro status | cat` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status | cat` with sudo
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status > status_out` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status > status_out` with sudo
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status --format tabular | cat` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status --format tabular > status_out` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro status --format json`.
      """
    When I run shell command `pro status --format json | cat` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro status --format json > status_out` as non-root
    Then I will see the following on stderr
      """
      """
    # populate esm-cache
    When I apt update
    And I run shell command `pro security-status | cat` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro security-status --format json`.
      """
    When I run shell command `pro security-status > status_out` as non-root
    Then I will see the following on stderr
      """
      WARNING: this output is intended to be human readable, and subject to change.
      In scripts, prefer using machine readable data from the `pro api` command,
      or use `pro security-status --format json`.
      """
    When I run shell command `pro security-status --format json | cat` as non-root
    Then I will see the following on stderr
      """
      """
    When I run shell command `pro security-status --format json > status_out` as non-root
    Then I will see the following on stderr
      """
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | mantic  | lxd-container |
      | noble   | lxd-container |

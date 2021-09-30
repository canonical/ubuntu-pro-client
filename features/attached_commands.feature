@uses.config.contract_token
Feature: Command behaviour when attached to an UA subscription

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached refresh in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua refresh` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `ua refresh` with sudo
        Then I will see the following on stdout:
            """
            Successfully processed your ua configuration.
            Successfully refreshed your subscription.
            """
        When I run `ua refresh config` with sudo
        Then I will see the following on stdout:
            """
            Successfully processed your ua configuration.
            """
        When I run `ua refresh contract` with sudo
        Then I will see the following on stdout:
            """
            Successfully refreshed your subscription.
            """
        When I run `ls /var/log/ubuntu-advantage*` as non-root
        Then I will see the following on stdout:
            """
            /var/log/ubuntu-advantage.log
            /var/log/ubuntu-advantage-timer.log
            """
        When I run `logrotate --force /etc/logrotate.d/ubuntu-advantage-tools` with sudo
        And I run `ls /var/log/ubuntu-advantage-*` as non-root
        Then I will see the following on stdout:
            """
            /var/log/ubuntu-advantage.log.1
            /var/log/ubuntu-advantage-timer.log.1
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached disable of an already disabled service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua disable livepatch` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        And I verify that running `ua disable livepatch` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            Livepatch is not currently enabled
            See: sudo ua status
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached disable of a service in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua disable foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        And I verify that running `ua disable foobar` `with sudo` exits `1`
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch, ros,
            ros-updates.
            """
        And I verify that running `ua disable esm-infra` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `ua disable esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance \(ESM\)
            """
        And I verify that running `apt update` `with sudo` exits `0`

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached detach in an ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua detach` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `ua detach --assume-yes` with sudo
        Then I will see the following on stdout:
            """
            Detach will disable the following services:
                esm-apps
                esm-infra
            Updating package lists
            Updating package lists
            This machine is now detached.
            """
       When I run `ua status --all` as non-root
       Then stdout matches regexp:
          """
          SERVICE       AVAILABLE  DESCRIPTION
          cc-eal        +<cc-eal>   +Common Criteria EAL2 Provisioning Packages
          cis           +<cis>      +Center for Internet Security Audit Tools
          esm-apps      +<esm-apps> +UA Apps: Extended Security Maintenance \(ESM\)
          esm-infra     +yes        +UA Infra: Extended Security Maintenance \(ESM\)
          fips          +<fips>     +NIST-certified core packages
          fips-updates  +<fips>     +NIST-certified core packages with priority security updates
          livepatch     +yes        +Canonical Livepatch service
          ros           +<ros>      +Security Updates for the Robot Operating System
          ros-updates   +<ros>      +All Updates for the Robot Operating System
          """
       And stdout matches regexp:
          """
          This machine is not attached to a UA subscription.
          """
       And I verify that running `apt update` `with sudo` exits `0`

       Examples: ubuntu release
           | release | esm-apps | cc-eal | cis | fips | fips-update | ros |
           | bionic  | yes      | no     | yes | yes  | yes         | yes  |
           | focal   | yes      | no     | yes | yes  | yes         | no  |
           | xenial  | yes      | yes    | yes | yes  | yes         | yes |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached auto-attach in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua auto-attach` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\).
            """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
            """
            This machine is already attached
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached show version in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua version` with sudo
        Then I will see the uaclient version on stdout
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout
        When I run `ua --version` with sudo
        Then I will see the uaclient version on stdout

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Unattached status in a ubuntu machine with feature overrides
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "cc-eal",
                            "entitled": false
                        }
                    ]
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
          disable_auto_attach: true
          other: false
        """
        And I attach `contract_token` with sudo
        And I run `ua status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        no
            """
        When I run `ua --version` as non-root
        Then I will see the uaclient version on stdout with features ` +disable_auto_attach +machine_token_overlay -other`
        When I run `ua version` as non-root
        Then I will see the uaclient version on stdout with features ` +disable_auto_attach +machine_token_overlay -other`
        When I run `ua auto-attach` with sudo
        Then stdout matches regexp:
        """
        Skipping auto-attach. Config disable_auto_attach is set.
        """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | hirsute |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached disable of different services in a ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        Then I verify that running `ua disable esm-infra livepatch foobar` `as non-root` exits `1`
        And stderr matches regexp:
            """
            This command must be run as root \(try using sudo\)
            """
        And I verify that running `ua disable esm-infra livepatch foobar` `with sudo` exits `1`
        And I will see the following on stdout:
            """
            Updating package lists
            Livepatch is not currently enabled
            See: sudo ua status
            """
        And stderr matches regexp:
            """
            Cannot disable unknown service 'foobar'.
            Try cc-eal, cis, esm-apps, esm-infra, fips, fips-updates, livepatch, ros,
            ros-updates.
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            esm-infra    +yes      +disabled +UA Infra: Extended Security Maintenance \(ESM\)
            """
        When I run `touch /var/run/reboot-required` with sudo
        And I run `touch /var/run/reboot-required.pkgs` with sudo
        And I run `ua enable esm-infra` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            UA Infra: ESM enabled
            """
        And stdout does not match regexp:
            """
            A reboot is required to complete install.
            """

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Help command on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua help esm-infra` with sudo
        Then I will see the following on stdout:
            """
            Name:
            esm-infra

            Entitled:
            yes

            Status:
            <infra-status>

            Help:
            esm-infra provides access to a private ppa which includes available high
            and critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main
            repository between the end of the standard Ubuntu LTS security
            maintenance and its end of life. It is enabled by default with
            Extended Security Maintenance (ESM) for UA Apps and UA Infra.
            You can find our more about the esm service at
            https://ubuntu.com/security/esm
            """
        When I run `ua help esm-infra --format json` with sudo
        Then I will see the following on stdout:
            """
            {"name": "esm-infra", "entitled": "yes", "status": "<infra-status>", "help": "esm-infra provides access to a private ppa which includes available high\nand critical CVE fixes for Ubuntu LTS packages in the Ubuntu Main\nrepository between the end of the standard Ubuntu LTS security\nmaintenance and its end of life. It is enabled by default with\nExtended Security Maintenance (ESM) for UA Apps and UA Infra.\nYou can find our more about the esm service at\nhttps://ubuntu.com/security/esm\n"}
            """
        And I verify that running `ua help invalid-service` `with sudo` exits `1`
        And I will see the following on stderr:
            """
            No help available for 'invalid-service'
            """
        When I run `ua --help` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Advantage services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - cis: Center for Internet Security Audit Tools
           \(https://ubuntu.com/security/certifications#cis\)
         - esm-infra: UA Infra: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `ua help` with sudo
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Advantage services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - cis: Center for Internet Security Audit Tools
           \(https://ubuntu.com/security/certifications#cis\)
         - esm-infra: UA Infra: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
        """
        When I run `ua help --all` as non-root
        Then stdout matches regexp:
        """
        Client to manage Ubuntu Advantage services on a machine.
         - cc-eal: Common Criteria EAL2 Provisioning Packages
           \(https://ubuntu.com/cc-eal\)
         - cis: Center for Internet Security Audit Tools
           \(https://ubuntu.com/security/certifications#cis\)
         - esm-apps: UA Apps: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - esm-infra: UA Infra: Extended Security Maintenance \(ESM\)
           \(https://ubuntu.com/security/esm\)
         - fips-updates: NIST-certified core packages with priority security updates
           \(https://ubuntu.com/security/certifications#fips\)
         - fips: NIST-certified core packages
           \(https://ubuntu.com/security/certifications#fips\)
         - livepatch: Canonical Livepatch service
           \(https://ubuntu.com/security/livepatch\)
         - ros-updates: All Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
         - ros: Security Updates for the Robot Operating System
           \(https://ubuntu.com/robotics/ros-esm\)
        """

        Examples: ubuntu release
           | release | infra-status |
           | bionic  | enabled      |
           | focal   | enabled      |
           | xenial  | enabled      |
           | hirsute | n/a          |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Enable command with invalid repositories in user machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua disable esm-infra` with sudo
        And I run `add-apt-repository ppa:cloud-init-dev/daily -y` with sudo, retrying exit [1]
        And I run `apt update` with sudo
        And I run `sed -i 's/ubuntu/ubun/' /etc/apt/sources.list.d/<ppa_file>.list` with sudo
        And I verify that running `ua enable esm-infra` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        One moment, checking your subscription first
        Updating package lists
        APT update failed.
        APT update failed to read APT config for the following URL:
        - http://ppa.launchpad.net/cloud-init-dev/daily/ubun
        """

        Examples: ubuntu release
           | release | ppa_file                           |
           | xenial  | cloud-init-dev-ubuntu-daily-xenial |
           | bionic  | cloud-init-dev-ubuntu-daily-bionic |
           | focal   | cloud-init-dev-ubuntu-daily-focal  |

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Run timer script on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `systemctl stop ua-timer.timer` with sudo
        And I attach `contract_token` with sudo
        Then I verify that running `ua config set update_messaging_timer=-2` `with sudo` exits `1`
        And stderr matches regexp:
        """
        Cannot set update_messaging_timer to -2: <value> for interval must be a positive integer.
        """
        When I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout matches regexp:
        """"
        "update_messaging":
        """
        And stdout matches regexp:
        """"
        "update_status":
        """
        When I run `ua config show` with sudo
        Then stdout matches regexp:
        """
        update_messaging_timer  +21600
        update_status_timer     +43200
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `ua config set update_messaging_timer=0` with sudo
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout does not match regexp:
        """"
        "update_messaging":
        """
        And stdout matches regexp:
        """"
        "update_status":
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: https://contracts.canonical.com
        data_dir: /var/lib/ubuntu-advantage
        log_file: /var/log/ubuntu-advantage.log
        log_level: debug
        security_url: https://ubuntu.com/security
        ua_config:
          apt_http_proxy: null
          apt_https_proxy: null
          http_proxy: null
          https_proxy: null
          update_messaging_timer: 14400
          update_status_timer: 0
          metering_timer: 0
        """
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout matches regexp:
        """"
        "update_messaging":
        """
        And stdout does not match regexp:
        """"
        "update_status":
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: https://contracts.canonical.com
        data_dir: /var/lib/ubuntu-advantage
        log_file: /var/log/ubuntu-advantage.log
        log_level: debug
        security_url: https://ubuntu.com/security
        ua_config:
          apt_http_proxy: null
          apt_https_proxy: null
          http_proxy: null
          https_proxy: null
          update_messaging_timer: -10
          update_status_timer: notanumber
          metering_timer: 0
        """
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that running `grep "Invalid value for update_messaging interval found in config." /var/log/ubuntu-advantage-timer.log` `with sudo` exits `0`
        And I verify that running `grep "Invalid value for update_status interval found in config." /var/log/ubuntu-advantage-timer.log` `with sudo` exits `0`
        And I verify that the timer interval for `update_messaging` is `21600`
        And I verify that the timer interval for `update_status` is `43200`

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | hirsute |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Run collect-logs on an attached machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I verify that running `ua collect-logs` `as non-root` exits `1`
        Then I will see the following on stderr:
             """
             This command must be run as root (try using sudo).
             """
        When I run `ua collect-logs` with sudo
        Then I verify that files exist matching `ua_logs.tar.gz`
        When I run `tar zxf ua_logs.tar.gz` as non-root
        Then I verify that files exist matching `logs/`
        When I run `sh -c "ls -1 logs/ | sort -d"` as non-root
        # On Xenial, the return value for inexistent services is the same as for dead ones (3).
        # So the -error suffix does not appear there.
        Then stdout matches regexp:
        """
        cloud-id.txt
        jobs-status.json
        journalctl.txt
        livepatch-status.txt-error
        systemd-timers.txt
        ua-auto-attach.path.txt(-error)?
        ua-auto-attach.service.txt(-error)?
        uaclient.conf
        ua-license-check.path.txt
        ua-license-check.service.txt
        ua-license-check.timer.txt
        ua-reboot-cmds.service.txt
        ua-status.json
        ua-timer.service.txt
        ua-timer.timer.txt
        ubuntu-advantage.log
        ubuntu-advantage-timer.log
        ubuntu-esm-apps.list
        ubuntu-esm-infra.list
        """
        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Run timer script to valid machine activity endpoint
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt install jq -y` with sudo
        And I save the `activityInfo.activityToken` value from the contract
        And I save the `activityInfo.activityID` value from the contract
        # normal metering call when activityId is set by attach response above, expect new
        # token and same id
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that `activityInfo.activityToken` value has been updated on the contract
        And I verify that `activityInfo.activityID` value has not been updated on the contract
        When I restore the saved `activityInfo.activityToken` value on contract
        And I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        # simulate "cloned" metering call where previously used activityToken is sent again,
        # expect new token and new id
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that `activityInfo.activityToken` value has been updated on the contract
        And I verify that `activityInfo.activityID` value has been updated on the contract
        # We are keeping this test to guarantee that the activityPingInterval is also updated
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                   "id": "testCID"
                },
                "machineId": "testMID"
            }
        }
        """
        And I create the file `/tmp/response-overlay.json` with the following:
        """
        {
            "https://contracts.canonical.com/v1/contracts/testCID/machine-activity/testMID": [
            {
              "code": 200,
              "response": {
                "activityToken": "test-activity-token",
                "activityID": "test-activity-id",
                "activityPingInterval": 123456789
              }
            }]
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
          serviceclient_url_responses: "/tmp/response-overlay.json"
        """
        When I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        Then I verify that running `grep -q activityInfo /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        And I verify that running `grep -q "\"activityToken\": \"test-activity-token\"" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        And I verify that running `grep -q "\"activityID\": \"test-activity-id\"" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        And I verify that running `grep -q "\"activityPingInterval\": 123456789" /var/lib/ubuntu-advantage/private/machine-token.json` `with sudo` exits `0`
        When I run `cat /var/lib/ubuntu-advantage/jobs-status.json` with sudo
        Then stdout matches regexp:
        """
        \"metering\"
        """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |

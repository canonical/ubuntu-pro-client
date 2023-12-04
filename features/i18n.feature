Feature: Pro supports multiple languages

    Scenario Outline: Translation works
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run shell command `LANGUAGE=pt_BR.UTF-8 pro security-status` as non-root
        Then stdout contains substring:
        """
        Esta máquina NÃO está vinculada a uma assinatura do Ubuntu Pro.
        """
        When I run shell command `LANGUAGE=pt_BR.UTF-8 pro status --all` as non-root
        Then stdout contains substring:
        """
        sim
        """
        Then stdout contains substring:
        """
        não
        """
        When I run `apt update` with sudo
        And I apt install `jq`
        And I run shell command `LANGUAGE=pt_BR.UTF-8 pro status --format json | jq .services[0].available` as non-root
        Then I will see the following on stdout:
        """
        "yes"
        """
        When I run `apt-get remove -y ubuntu-pro-client-l10n` with sudo
        When I run shell command `LANGUAGE=pt_BR.UTF-8 pro security-status` as non-root
        Then stdout contains substring:
        """
        This machine is NOT attached to an Ubuntu Pro subscription.
        """
        Examples: ubuntu release
           | release | machine_type  |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    Scenario Outline: Translation works
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run shell command `LANGUAGE=pt_BR.UTF-8 pro security-status` as non-root
        Then stdout contains substring:
        """
        Ubuntu Pro não está disponível para versões do Ubuntu não LTS.
        """
        When I run shell command `LANGUAGE=pt_BR.UTF-8 pro status --all` as non-root
        Then stdout contains substring:
        """
        não
        """
        When I run `apt update` with sudo
        And I apt install `jq`
        And I run shell command `LANGUAGE=pt_BR.UTF-8 pro status --format json | jq .result` as non-root
        Then I will see the following on stdout:
        """
        "success"
        """
        When I run `apt-get remove -y ubuntu-pro-client-l10n` with sudo
        When I run shell command `LANGUAGE=pt_BR.UTF-8 pro security-status` as non-root
        Then stdout contains substring:
        """
        Ubuntu Pro is not available for non-LTS releases.
        """
        Examples: ubuntu release
           | release | machine_type  |
           | mantic  | lxd-container |

    # Note: Translations do work on xenial, but our test environment triggers a bug in python that
    #       causes it to think we're in an ascii-only environment
    Scenario Outline: Translation doesn't error when python thinks it's ascii only
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run shell command `env LC_CTYPE=pt_BR.UTF-8 LANGUAGE=pt_BR.UTF-8 python3 -c \"import sys; print(sys.stdout.encoding)\"` as non-root
        Then I will see the following on stdout:
        """
        ANSI_X3.4-1968
        """
        When I run shell command `env LC_CTYPE=pt_BR.UTF-8 LANGUAGE=pt_BR.UTF-8 pro security-status` as non-root
        Then stdout contains substring:
        """
        This machine is NOT attached to an Ubuntu Pro subscription.
        """
        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |

    Scenario Outline: apt-hook translations work
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `apt-get update` with sudo
        When I run `apt-get upgrade -y` with sudo
        When I run `pro detach --assume-yes` with sudo
        When I run `apt-get update` with sudo
        When I run `apt-get install hello` with sudo
        When I attach `contract_token` with sudo
        When I run shell command `LANGUAGE=pt_BR.UTF-8 apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        1 atualização de segurança do esm-apps
        """
        Examples: ubuntu release
           | release | machine_type  |
           | focal   | lxd-container |

    @uses.config.contract_token
    Scenario Outline: Pro client's commands run successfully in a different locale
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        ## Change the locale
        When I run `apt install language-pack-fr -y` with sudo
        And I run `update-locale LANG=fr_FR.UTF-8` with sudo
        And I reboot the machine
        And I run `cat /etc/default/locale` as non-root
        Then stdout matches regexp:
        """
        LANG=fr_FR.UTF-8
        """
        #Attach invalid token
        When I verify that running `pro attach INVALID_TOKEN` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        Invalid token. See https://ubuntu.com/pro
        """
        When I run `lscpu` as non-root
        Then stdout does not match regexp:
        """
        Architecture:
        """
        When I run `apt update` with sudo
        Then stdout does not match regexp:
        """
        Hit
        """
        When I verify that running `pro attach INVALID_TOKEN` `as non-root` exits `1`
        Then I will see the following on stderr:
         """
         This command must be run as root (try using sudo).
         """
        When I verify that running `pro attach invalid-token --format json` `with sudo` exits `1`
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [{"message": "Invalid token. See https://ubuntu.com/pro/dashboard", "message_code": "attach-invalid-token", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
        """
        When I attach `contract_token` with sudo
        # Refresh command
        When I run `pro refresh` with sudo
        Then I will see the following on stdout:
        """
        Successfully processed your pro configuration.
        Successfully refreshed your subscription.
        Successfully updated Ubuntu Pro related APT and MOTD messages.
        """
    # auto-attach command
        When I verify that running `pro auto-attach` `with sudo` exits `2`
        Then stderr matches regexp:
        """
        This machine is already attached to '.+'
        To use a different subscription first run: sudo pro detach.
            """
        # status command
        When I run `pro status --format json` as non-root
        Then stdout is a json matching the `ua_status` schema
        When I run `pro status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_status` schema
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "effectiveTo": null
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
        """
        And I run `pro status` with sudo
        Then stdout contains substring:
        """
        Valid until: Unknown/Expired
        """
        # api command invalid endpoint
        When I verify that running `pro api invalid.endpoint` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        {\"_schema_version\": \"v1\", \"data\": {\"meta\": {\"environment_vars\": \[]}}, \"errors\": \[{\"code\": \"api\-invalid\-endpoint", \"meta\": {\"endpoint\": \"invalid.endpoint\"}, \"title\": \"'invalid\.endpoint' is not a valid endpoint\"}], \"result\": \"failure\", \"version\": \".*\", \"warnings\": \[]}
        """
        When I verify that running `pro api u.pro.version.v1 --args extra=arg` `with sudo` exits `1`
        Then stdout matches regexp:
        """
        {\"_schema_version\": \"v1\", \"data\": {\"meta\": {\"environment_vars\": \[]}}, \"errors\": \[{\"code\": \"api\-no\-argument\-for\-endpoint\", \"meta\": {\"endpoint\": \"u.pro.version.v1\"}, \"title\": \"u\.pro\.version\.v1 accepts no arguments\"}], \"result\": \"failure\", \"version\": \".*\", \"warnings\": \[]}
        """
        # api command valid endpoint
        When I run `pro api u.pro.version.v1` with sudo
        Then stdout matches regexp:
        """
        {\"_schema_version\": \"v1\", \"data\": {\"attributes\": {\"installed_version\": \".*\"}, \"meta\": {\"environment_vars\": \[]}, \"type\": \"Version\"}, \"errors\": \[], \"result\": \"success\", \"version\": \".*\", \"warnings\": \[]}
        """
        When I run `UA_LOG_FILE=/tmp/some_file OTHER_ENVVAR=not_there pro api u.pro.version.v1` with sudo
        Then stdout matches regexp:
        """
        {\"_schema_version\": \"v1\", \"data\": {\"attributes\": {\"installed_version\": \".*\"}, \"meta\": {\"environment_vars\": \[{\"name\": \"UA_LOG_FILE\", \"value\": \"\/tmp\/some_file\"}]}, \"type\": \"Version\"}, \"errors\": \[], \"result\": \"success\", \"version\": \".*\", \"warnings\": \[]}
        """
        When I run `ua api u.pro.attach.auto.should_auto_attach.v1` with sudo
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"should_auto_attach": false}, "meta": {"environment_vars": \[\]}, "type": "ShouldAutoAttach"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        # version
        When I run `pro version` as non-root
        Then I will see the uaclient version on stdout
        When I run `pro version` with sudo
        Then I will see the uaclient version on stdout
        When I run `pro --version` as non-root
        Then I will see the uaclient version on stdout
        When I run `pro --version` with sudo
        Then I will see the uaclient version on stdout
        Examples: ubuntu release
           | release | machine_type  |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | xenial  | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

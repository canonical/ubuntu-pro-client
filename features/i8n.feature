Feature: Pro supports multiple languages

    @series.all
    @uses.config.machine_type.lxd-container
    @uses.config.contract_token
    Scenario Outline: Pro client's commands run successfully
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        This machine is already attached to 'UA Client Test'
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
           | release |
           | bionic  |
           | focal   |
           | xenial  |
           | jammy   |
           | lunar   |
           | mantic  |

@uses.config.contract_token
@uses.config.landscape_registration_key
@uses.config.landscape_api_access_key
@uses.config.landscape_api_secret_key
Feature: Enable landscape on Ubuntu

    @series.mantic
    @uses.config.machine_type.any
    @uses.config.machine_type.lxd-container
    Scenario Outline: Enable Landscape non-interactively
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo and options `--no-auto-enable`

        Then I verify that running `pro enable landscape` `as non-root` exits `1`
        And I will see the following on stderr:
        """
        This command must be run as root (try using sudo).
        """

        When I run `pro enable landscape -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key} --silent` with sudo
        Then stdout contains substring:
        """
        One moment, checking your subscription first
        Updating package lists
        Installing landscape-client
        Executing `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key <REDACTED> --silent`
        """
        Then stdout contains substring
        """
        System successfully registered.
        """
        When I run `pro status` as non-root
        Then stdout matches regexp:
        """
        landscape +yes +enabled
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +enabled
        """

        When I run `systemctl stop landscape-client` with sudo
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +warning
        """
        Then stdout contains substring:
        """
        Landscape is installed and configured and registered but not running.
        Run `sudo landscape-config` to start it, or run `sudo pro disable landscape`
        """

        When I run `rm /etc/landscape/client.conf` with sudo
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +warning
        """
        Then stdout contains substring:
        """
        Landscape is installed but not configured.
        Run `sudo landscape-config` to set it up, or run `sudo pro disable landscape`
        """

        When I run `sudo pro disable landscape` with sudo
        Then I will see the following on stdout:
        """
        Executing `landscape-config --disable`
        Failed running command 'landscape-config --disable' [exit(1)]. Message: error: config file /etc/landscape/client.conf can't be read
        Backing up /etc/landscape/client.conf as /etc/landscape/client.conf.pro-disable-backup
        [Errno 2] No such file or directory: '/etc/landscape/client.conf' -> '/etc/landscape/client.conf.pro-disable-backup'
        Uninstalling landscape-client
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +disabled
        """

        # Enable with assume-yes
        When I run `pro enable landscape --assume-yes -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key}` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Updating package lists
        Installing landscape-client
        Executing `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key <REDACTED> --silent`
        Landscape enabled
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +enabled
        """
        When I run `sudo pro disable landscape` with sudo

        # Fail to enable with assume-yes
        When I verify that running `pro enable landscape --assume-yes -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa` `with sudo` exits `1`
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Updating package lists
        Installing landscape-client
        Executing `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --silent`
        Created symlink /etc/systemd/system/multi-user.target.wants/landscape-client.service → /lib/systemd/system/landscape-client.service.
        Invalid account name or registration key.
        Could not enable Landscape.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +warning
        """
        Then stdout contains substring:
        """
        Landscape is installed and configured but not registered.
        Run `sudo landscape-config` to register, or run `sudo pro disable landscape`
        """
        When I run `sudo pro disable landscape` with sudo

        # Enable with assume-yes and format json
        When I run `pro enable landscape --assume-yes --format=json -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key}` with sudo
        Then I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["landscape"], "result": "success", "warnings": []}
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +enabled
        """
        When I run `sudo pro disable landscape` with sudo

        # Fail to enable with assume-yes and format json
        When I verify that running `pro enable landscape --assume-yes --format=json -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa` `with sudo` exits `1`
        Then I will see the following on stdout:
        """
        {"_schema_version": "0.1", "errors": [{"additional_info": {"stderr": "Created symlink /etc/systemd/system/multi-user.target.wants/landscape-client.service \u2192 /lib/systemd/system/landscape-client.service.\nInvalid account name or registration key.", "stdout": "Please wait..."}, "message": "landscape-config command failed", "message_code": "landscape-config-failed", "service": "landscape", "type": "service"}], "failed_services": ["landscape"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +warning
        """
        Then stdout contains substring:
        """
        Landscape is installed and configured but not registered.
        Run `sudo landscape-config` to register, or run `sudo pro disable landscape`
        """
        When I run `sudo pro disable landscape` with sudo

        # cleanup
        Then I reject all pending computers on Landscape
        Examples: ubuntu release
            | release | machine_type  |
            | mantic  | lxd-container |

    @series.mantic
    @uses.config.machine_type.any
    @uses.config.machine_type.lxd-container
    Scenario Outline: Enable Landscape interactively
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo and options `--no-auto-enable`

        Then I verify that running `pro enable landscape` `as non-root` exits `1`
        And I will see the following on stderr:
        """
        This command must be run as root (try using sudo).
        """

        When I run `pro enable landscape` `with sudo` and the following stdin
        # This will change in the future, but right now the lines are:
        # allow starting on boot
        # computer title
        # account name
        # registration key
        # confirm registration key
        # http proxy
        # https proxy
        # enable script execution
        # access group
        # tags
        # request registration
        """
        y
        $behave_var{machine-name system-under-test}
        pro-client-qa
        $behave_var{config landscape_registration_key}
        $behave_var{config landscape_registration_key}


        n


        y
        """
        Then stdout contains substring:
        """
        One moment, checking your subscription first
        Updating package lists
        Installing landscape-client
        Executing `landscape-config`
        """
        Then stdout contains substring:
        """
        System successfully registered.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +enabled
        """
        When I run `pro disable landscape` with sudo

        When I verify that running `pro enable landscape` `with sudo` and the following stdin exits `1`
        """
        y
        $behave_var{machine-name system-under-test}
        pro-client-qa
        wrong
        wrong


        n


        y
        """
        Then stdout contains substring:
        """
        One moment, checking your subscription first
        Updating package lists
        Installing landscape-client
        Executing `landscape-config`
        """
        Then stderr contains substring:
        """
        Invalid account name or registration key.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        landscape +yes +warning
        """
        Then stdout contains substring:
        """
        Landscape is installed and configured but not registered.
        Run `sudo landscape-config` to register, or run `sudo pro disable landscape`
        """

        # cleanup
        Then I reject all pending computers on Landscape
        Examples: ubuntu release
            | release | machine_type  |
            | mantic  | lxd-container |

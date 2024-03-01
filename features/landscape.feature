@uses.config.contract_token @uses.config.landscape_registration_key @uses.config.landscape_api_access_key @uses.config.landscape_api_secret_key
Feature: Enable landscape on Ubuntu

  Scenario Outline: Enable Landscape non-interactively
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    Then I verify that running `pro enable landscape` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I run `pro enable landscape -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key} --silent` with sudo
    Then stdout contains substring:
      """
      One moment, checking your subscription first
      Updating standard Ubuntu package lists
      Installing landscape-client
      Executing `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key <REDACTED> --silent`
      """
    Then stdout contains substring
      """
      Registration request sent successfully.
      """
    And I verify that `landscape` is enabled
    When I run `sudo pro disable landscape` with sudo
    Then I verify that `landscape` is disabled
    # Enable with assume-yes
    When I run `pro enable landscape --assume-yes -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key}` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating standard Ubuntu package lists
      Installing landscape-client
      Executing `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key <REDACTED> --silent`
      Landscape enabled
      """
    And I verify that `landscape` is enabled
    # stopping the service effectively disables it
    When I run `systemctl stop landscape-client` with sudo
    Then I verify that `landscape` is disabled
    When I verify that running `sudo pro disable landscape` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      Landscape is not currently enabled
      See: sudo pro status
      """
    # Fail to enable with assume-yes
    When I verify that running `pro enable landscape --assume-yes -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key wrong` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating standard Ubuntu package lists
      Installing landscape-client
      Executing `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key <REDACTED> --silent`
      Invalid account name or registration key.
      Could not enable Landscape.
      landscape-config command failed
      """
    # This will become obsolete soon: #2864
    When I run `pro status` with sudo
    # I am keeping this check until the non-root landscape-config check works as expected
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
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      landscape +yes +disabled
      """
    # Enable with assume-yes and format json
    When I run `pro enable landscape --assume-yes --format=json -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key}` with sudo
    Then I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [], "failed_services": [], "needs_reboot": false, "processed_services": ["landscape"], "result": "success", "warnings": []}
      """
    And I verify that `landscape` is enabled
    When I run `sudo pro disable landscape` with sudo
    # Fail to enable with assume-yes and format json
    When I verify that running `pro enable landscape --assume-yes --format=json -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key wrong` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      {"_schema_version": "0.1", "errors": [{"additional_info": {"stderr": "Invalid account name or registration key.", "stdout": ""}, "message": "landscape-config command failed", "message_code": "landscape-config-failed", "service": "landscape", "type": "service"}], "failed_services": ["landscape"], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
      """
    # This will become obsolete soon: #2864
    When I run `pro status` with sudo
    # I am keeping this check until the non-root landscape-config check works as expected
    Then stdout matches regexp:
      """
      landscape +yes +warning
      """
    Then stdout contains substring:
      """
      Landscape is installed and configured but not registered.
      Run `sudo landscape-config` to register, or run `sudo pro disable landscape`
      """

    Examples: ubuntu release
      | release | machine_type  |
      | mantic  | lxd-container |

  Scenario Outline: Enable Landscape interactively
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    Then I verify that running `pro enable landscape` `as non-root` exits `1`
    And I will see the following on stderr:
      """
      This command must be run as root (try using sudo).
      """
    When I run `pro enable landscape` `with sudo` and the following stdin
      # This will change in the future, but right now the lines are:
      # use self-hosted?
      # computer title
      # account name
      # registration key
      # confirm registration key
      # http proxy
      # https proxy
      # request registration
      """
      n
      $behave_var{machine-name system-under-test}
      pro-client-qa
      $behave_var{config landscape_registration_key}
      $behave_var{config landscape_registration_key}


      y
      """
    Then stdout contains substring:
      """
      One moment, checking your subscription first
      Updating standard Ubuntu package lists
      Installing landscape-client
      Executing `landscape-config`
      """
    Then stdout contains substring:
      """
      Registration request sent successfully.
      """
    And I verify that `landscape` is enabled
    When I run `pro disable landscape` with sudo
    When I verify that running `pro enable landscape` `with sudo` and the following stdin exits `1`
      """
      n
      $behave_var{machine-name system-under-test}
      pro-client-qa
      wrong
      wrong


      y
      """
    Then stdout contains substring:
      """
      One moment, checking your subscription first
      Updating standard Ubuntu package lists
      Installing landscape-client
      Executing `landscape-config`
      """
    And stderr contains substring:
      """
      Invalid account name or registration key.
      """
    When I run `pro status` with sudo
    Then stdout contains substring:
      """
      Landscape is installed and configured but not registered.
      Run `sudo landscape-config` to register, or run `sudo pro disable landscape`
      """

    Examples: ubuntu release
      | release | machine_type  |
      | mantic  | lxd-container |

  Scenario Outline: Easily re-enable Landscape non-interactively after a disable
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro enable landscape --assume-yes -- --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key}` with sudo
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      Updating standard Ubuntu package lists
      Installing landscape-client
      Executing `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key <REDACTED> --silent`
      Landscape enabled
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      landscape +yes +enabled
      """
    When I run `pro disable landscape` with sudo
    Then I will see the following on stdout:
      """
      Executing `landscape-config --disable`
      /etc/landscape/client.conf contains your landscape-client configuration.
      To re-enable Landscape with the same configuration, run:
          sudo pro enable landscape --assume-yes
      """
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      landscape +yes +disabled
      """
    When I run `pro enable landscape --assume-yes` with sudo
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      landscape +yes +enabled
      """
    When I run shell command `cat /etc/landscape/client.conf | grep computer_title` with sudo
    Then I will see the following on stdout:
      """
      computer_title = $behave_var{machine-name system-under-test}
      """
    When I run shell command `cat /etc/landscape/client.conf | grep account_name` with sudo
    Then I will see the following on stdout:
      """
      account_name = pro-client-qa
      """
    # Now do the same test but with a full detach
    When I run `pro detach --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      Detach will disable the following service:
          landscape
      Executing `landscape-config --disable`
      /etc/landscape/client.conf contains your landscape-client configuration.
      To re-enable Landscape with the same configuration, run:
          sudo pro enable landscape --assume-yes

      This machine is now detached.
      """
    When I run `pro api u.pro.status.is_attached.v1` with sudo
    Then stdout contains substring:
      """
      "is_attached": false
      """
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro enable landscape --assume-yes` with sudo
    When I run `pro status` with sudo
    Then stdout matches regexp:
      """
      landscape +yes +enabled
      """
    When I run shell command `cat /etc/landscape/client.conf | grep computer_title` with sudo
    Then I will see the following on stdout:
      """
      computer_title = $behave_var{machine-name system-under-test}
      """
    When I run shell command `cat /etc/landscape/client.conf | grep account_name` with sudo
    Then I will see the following on stdout:
      """
      account_name = pro-client-qa
      """

    Examples: ubuntu release
      | release | machine_type  |
      | mantic  | lxd-container |

  Scenario Outline: Detaching/reattaching on an unsupported release does not affect landscape
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro status` with sudo
    Then stdout does not contain substring:
      """
      landscape
      """
    When I apt install `landscape-client`
    # assert pre-enabled state
    When I verify that running `systemctl is-active landscape-client` `with sudo` exits `3`
    Then I will see the following on stdout:
      """
      inactive
      """
    # enable with landscape-config directly
    When I run `landscape-config --computer-title $behave_var{machine-name system-under-test} --account-name pro-client-qa --registration-key $behave_var{config landscape_registration_key} --silent` with sudo
    Then I will see the following on stdout:
      """
      Please wait...
      System successfully registered.
      """
    # assert that landscape is running, but pro doesn't care
    When I verify that running `systemctl is-active landscape-client` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      active
      """
    When I run `pro status` with sudo
    Then stdout does not contain substring:
      """
      landscape
      """
    # disable refuses
    When I verify that running `pro disable landscape` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      Disabling Landscape with pro is not supported.
      See: sudo pro status
      """
    # detach doesn't touch it
    When I run `pro detach --assume-yes` with sudo
    Then I will see the following on stdout:
      """
      This machine is now detached.
      """
    # still running
    When I verify that running `systemctl is-active landscape-client` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      active
      """
    # re-attaching doesn't affect it either
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    # still running
    When I verify that running `systemctl is-active landscape-client` `with sudo` exits `0`
    Then I will see the following on stdout:
      """
      active
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

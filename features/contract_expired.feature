Feature: End of contract messages

  @vpn @uses.config.contract_token
  Scenario Outline: Display expired messages in all relevant places
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt upgrade
    When I apt install `hello update-motd`
    When I set the test contract expiration date to `$behave_var{today +1}`
    When I attach `contract_token_staging_expired_sometimes` with sudo and options `--no-auto-enable`
    # HACK NOTICE: This part relies on implementation details of pro-client
    # we hack apt-helper to let pro enable go through to simulate being expired with services enabled
    # we can't just enable before expiring the contract because esm-auth is cached
    When I create the file `/usr/bin/apt-helper-always-true` with the following
      """
      #!/usr/bin/bash
      true
      """
    When I run `chmod +x /usr/bin/apt-helper-always-true` with sudo
    When I run `mv /usr/lib/apt/apt-helper /usr/lib/apt/apt-helper.backup` with sudo
    When I run `ln -s /usr/bin/apt-helper-always-true /usr/lib/apt/apt-helper` with sudo
    When I run `pro enable esm-apps` with sudo
    When I set the test contract expiration date to `$behave_var{today -20}`
    When I run `pro refresh` with sudo
    When I run `pro status` with sudo
    Then stdout contains substring:
      """
      *Your Ubuntu Pro subscription has EXPIRED*
      Renew your subscription at https://ubuntu.com/pro/dashboard
      """
    When I verify that running `apt upgrade -y` `with sudo` exits `100`
    Then stdout contains substring:
      """
      #
      # *Your Ubuntu Pro subscription has EXPIRED*
      # Renew your subscription at https://ubuntu.com/pro/dashboard
      #
      The following packages will fail to download because your Ubuntu Pro subscription has expired
        hello
      Renew your subscription or `sudo pro detach` to remove these errors
      """
    And stderr matches regexp:
      """
      E: Failed to fetch https://esm\.staging\.ubuntu\.com/apps/ubuntu/pool/main/h/hello/hello_(.*)\.deb  401  Unauthorized \[IP: (.*) 443\]
      """
    When I run `update-motd` with sudo
    Then stdout contains substring:
      """
      *Your Ubuntu Pro subscription has EXPIRED*
      1 additional security update requires Ubuntu Pro with 'esm-apps' enabled.
      Renew your subscription at https://ubuntu.com/pro/dashboard
      """
    When I run `pro disable esm-apps` with sudo
    When I verify that running `pro enable esm-apps` `with sudo` exits `1`
    Then I will see the following on stdout:
      """
      One moment, checking your subscription first
      *Your Ubuntu Pro subscription has EXPIRED*
      Renew your subscription at https://ubuntu.com/pro/dashboard
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | lxd-container |

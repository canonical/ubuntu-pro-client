Feature: Command behaviour when auto-attached in an ubuntu PRO image

  Scenario Outline: Proxy auto-attach on a cloud Ubuntu Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    Given a `focal` `<machine_type>` machine named `proxy` with ingress ports `3389`
    When I apt install `squid` on the `proxy` machine
    And I add this text on `/etc/squid/squid.conf` on `proxy` above `http_access deny all`:
      """
      dns_v4_first on\nacl all src 0.0.0.0\/0\nhttp_port 3389\nhttp_access allow all
      """
    And I run `systemctl restart squid.service` `with sudo` on the `proxy` machine
    # This also tests that legacy `ua_config` settings still work
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      ua_config:
        http_proxy: http://$behave_var{machine-ip proxy}:3389
        https_proxy: http://$behave_var{machine-ip proxy}:3389
      """
    And I verify `/var/log/squid/access.log` is empty on `proxy` machine
    When I run `pro auto-attach` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `livepatch` is enabled
    When I run `pro enable <cis_or_usg>` with sudo
    Then I verify that `<cis_or_usg>` is enabled
    When I run `pro disable <cis_or_usg>` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      """
    And I verify that `<cis_or_usg>` is disabled
    When I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
    Then stdout matches regexp:
      """
      .*CONNECT contracts.canonical.com.*
      """
    And stdout does not match regexp:
      """
      .*CONNECT 169.254.169.254.*
      """
    And stdout does not match regexp:
      """
      .*CONNECT metadata.*
      """

    Examples: ubuntu release
      | release | machine_type | fips-s   | cc-eal-s | cis-s    | livepatch-s | lp-desc                                    | cis_or_usg |
      | xenial  | aws.pro      | disabled | disabled | disabled | enabled     | Canonical Livepatch service                | cis        |
      | xenial  | azure.pro    | disabled | disabled | disabled | enabled     | Canonical Livepatch service                | cis        |
      | xenial  | gcp.pro      | n/a      | disabled | disabled | warning     | Current kernel is not covered by livepatch | cis        |
      | bionic  | aws.pro      | disabled | disabled | disabled | enabled     | Canonical Livepatch service                | cis        |
      | bionic  | azure.pro    | disabled | disabled | disabled | enabled     | Canonical Livepatch service                | cis        |
      | bionic  | gcp.pro      | disabled | disabled | disabled | enabled     | Canonical Livepatch service                | cis        |
      | focal   | aws.pro      | disabled | n/a      | disabled | enabled     | Canonical Livepatch service                | usg        |
      | focal   | azure.pro    | disabled | n/a      | disabled | enabled     | Canonical Livepatch service                | usg        |
      | focal   | gcp.pro      | disabled | n/a      | disabled | enabled     | Canonical Livepatch service                | usg        |

  Scenario Outline: Attached refresh in an Ubuntu pro cloud machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      log_level: debug
      """
    And I run `pro auto-attach` with sudo
    Then I verify that `esm-apps` is enabled
    And I verify that `esm-infra` is enabled
    And I verify that `livepatch` is enabled
    When I run `systemctl start ua-auto-attach.service` with sudo
    And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
    Then stdout matches regexp:
      """
      .*status=0\/SUCCESS.*
      """
    And stdout matches regexp:
      """
      Active: inactive \(dead\).*
      \s*Condition: start condition (failed|unmet).*
      .*ConditionPathExists=!/var/lib/ubuntu-advantage/private/machine-token.json was not met
      """
    When I verify that running `pro auto-attach` `with sudo` exits `2`
    Then stderr matches regexp:
      """
      This machine is already attached to '.*'
      To use a different subscription first run: sudo pro detach.
      """
    When I run `apt-cache policy` with sudo
    Then apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
      """
    And apt-cache policy for the following url has priority `510`
      """
      https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """
    And I ensure apt update runs without errors
    When I apt install `<infra-pkg>/<release>-infra-security`
    And I run `apt-cache policy <infra-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
      """
    And stdout matches regexp:
      """
      Installed: .*[~+]esm
      """
    When I apt install `<apps-pkg>/<release>-apps-security`
    And I run `apt-cache policy <apps-pkg>` as non-root
    Then stdout matches regexp:
      """
      \s*\*\*\* .* 510
      \s*510 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
      """
    When I create the file `/var/lib/ubuntu-advantage/marker-reboot-cmds-required` with the following:
      """
      """
    And I reboot the machine
    And I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`
    Then stdout matches regexp:
      """
      .*status=0\/SUCCESS.*
      """
    When I run `ua api u.pro.attach.auto.should_auto_attach.v1` with sudo
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"should_auto_attach": true}, "meta": {"environment_vars": \[\]}, "type": "ShouldAutoAttach"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
      """

    Examples: ubuntu release
      | release | machine_type | infra-pkg | apps-pkg |
      | xenial  | aws.pro      | libkrad0  | jq       |
      | xenial  | azure.pro    | libkrad0  | jq       |
      | xenial  | gcp.pro      | libkrad0  | jq       |
      | bionic  | aws.pro      | libkrad0  | bundler  |
      | bionic  | azure.pro    | libkrad0  | bundler  |
      | bionic  | gcp.pro      | libkrad0  | bundler  |
      | focal   | aws.pro      | hello     | ant      |
      | focal   | azure.pro    | hello     | ant      |
      | focal   | gcp.pro      | hello     | ant      |
      | jammy   | aws.pro      | hello     | hello    |
      | jammy   | azure.pro    | hello     | hello    |
      | jammy   | gcp.pro      | hello     | hello    |
      | noble   | aws.pro      | hello     | hello    |
      | noble   | azure.pro    | hello     | hello    |
      | noble   | gcp.pro      | hello     | hello    |

  Scenario Outline: Auto-attach service works on Pro Machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `systemctl start ua-auto-attach.service` with sudo
    And I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    And I reboot the machine
    And I run `pro status --wait` with sudo
    And I run `pro security-status --format json` with sudo
    Then stdout matches regexp:
      """
      "attached": true
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | aws.pro      |
      | xenial  | azure.pro    |
      | xenial  | gcp.pro      |
      | bionic  | aws.pro      |
      | bionic  | azure.pro    |
      | bionic  | gcp.pro      |
      | focal   | aws.pro      |
      | focal   | azure.pro    |
      | focal   | gcp.pro      |
      | jammy   | aws.pro      |
      | jammy   | azure.pro    |
      | jammy   | gcp.pro      |
      | noble   | aws.pro      |
      | noble   | azure.pro    |
      | noble   | gcp.pro      |

  Scenario Outline: Auto-attach no-op when cloud-init has ubuntu_advantage on userdata
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed adding this cloud-init user_data:
      # This user_data should not do anything, just guarantee that the ua-auto-attach service
      # does nothing
      """
      <cloud_init_key>:
        features:
          disable_auto_attach: true
      """
    When I run `cloud-init query userdata` with sudo
    Then stdout matches regexp:
      """
      <cloud_init_key>:
        features:
          disable_auto_attach: true
      """
    # On GCP, this service will auto-attach the machine automatically after we override
    # the uaclient.conf file. To guarantee that we are not auto-attaching on reboot
    # through the ua-auto-attach.service, we are masking it
    When I run `systemctl mask ubuntu-advantage.service` with sudo
    And I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
      """
      contract_url: 'https://contracts.canonical.com'
      data_dir: /var/lib/ubuntu-advantage
      log_level: debug
      log_file: /var/log/ubuntu-advantage.log
      """
    And I reboot the machine
    And I run `pro status --wait` with sudo
    And I run `pro security-status --format json` with sudo
    Then stdout matches regexp:
      """
      "attached": false
      """
    When I run `journalctl -u ua-auto-attach.service` as non-root
    Then stdout matches regexp:
      """
      cloud-init userdata has ubuntu-advantage key.
      """
    And stdout matches regexp:
      """
      Skipping auto-attach and deferring to cloud-init to setup and configure auto-attach
      """
    When I run `cloud-init status` with sudo
    Then stdout matches regexp:
      """
      status: done
      """

    Examples: ubuntu release
      | release | machine_type | cloud_init_key   |
      | xenial  | aws.pro      | ubuntu_advantage |
      | xenial  | azure.pro    | ubuntu_advantage |
      | xenial  | gcp.pro      | ubuntu_advantage |
      | bionic  | aws.pro      | ubuntu_advantage |
      | bionic  | azure.pro    | ubuntu_advantage |
      | bionic  | gcp.pro      | ubuntu_advantage |
      # Keep ubuntu_advantage for focal/jammy to make sure it still works there
      | focal   | aws.pro      | ubuntu_advantage |
      | focal   | azure.pro    | ubuntu_advantage |
      | focal   | gcp.pro      | ubuntu_advantage |
      | jammy   | aws.pro      | ubuntu_advantage |
      | jammy   | azure.pro    | ubuntu_advantage |
      | jammy   | gcp.pro      | ubuntu_advantage |
      | noble   | aws.pro      | ubuntu_pro       |
      | noble   | azure.pro    | ubuntu_pro       |
      | noble   | gcp.pro      | ubuntu_pro       |

  Scenario Outline: Unregistered Pro machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro auto-attach` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      Failed to identify this image as a valid Ubuntu Pro image.
      Details:
      missing instance information
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | aws.generic  |
      | bionic  | aws.generic  |
      | focal   | aws.generic  |
      | jammy   | aws.generic  |
      | noble   | aws.generic  |

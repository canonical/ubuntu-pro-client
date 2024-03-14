@uses.config.contract_token
Feature: FIPS enablement in cloud based machines

  Scenario Outline: Attached enable of FIPS services in an ubuntu gcp vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    Then I verify that running `pro enable <fips_service> --assume-yes` `with sudo` exits `1`
    And stdout matches regexp:
      """
      Ubuntu <release_title> does not provide a GCP optimized FIPS kernel
      """

    Examples: fips
      | release | machine_type | release_title | fips_service |
      | xenial  | gcp.generic  | Xenial        | fips         |
      | xenial  | gcp.generic  | Xenial        | fips-updates |

  Scenario Outline: FIPS unholds packages
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
    When I run `pro disable fips --assume-yes` with sudo
    And I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then I will see the following on stdout:
      """
      openssh-client was already not hold.
      openssh-server was already not hold.
      strongswan was already not hold.
      """
    When I reboot the machine
    Then I verify that `openssh-server` installed version matches regexp `fips`
    And I verify that `openssh-client` installed version matches regexp `fips`
    And I verify that `strongswan` installed version matches regexp `fips`
    And I verify that `openssh-server-hmac` installed version matches regexp `fips`
    And I verify that `openssh-client-hmac` installed version matches regexp `fips`
    And I verify that `strongswan-hmac` installed version matches regexp `fips`

    Examples: ubuntu release
      | release | machine_type  | fips-apt-source                                |
      | xenial  | aws.generic   | https://esm.ubuntu.com/fips/ubuntu xenial/main |
      | xenial  | azure.generic | https://esm.ubuntu.com/fips/ubuntu xenial/main |

  Scenario Outline: FIPS unholds packages
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
    When I run `pro disable fips --assume-yes` with sudo
    And I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then I will see the following on stdout:
      """
      openssh-client was already not hold.
      openssh-server was already not hold.
      strongswan was already not hold.
      """
    When I reboot the machine
    Then I verify that `openssh-server` installed version matches regexp `fips`
    And I verify that `openssh-client` installed version matches regexp `fips`
    And I verify that `strongswan` installed version matches regexp `fips`
    And I verify that `openssh-server-hmac` installed version matches regexp `fips`
    And I verify that `openssh-client-hmac` installed version matches regexp `fips`
    And I verify that `strongswan-hmac` installed version matches regexp `fips`

    Examples: ubuntu release
      | release | machine_type  | fips-apt-source                                |
      | bionic  | aws.generic   | https://esm.ubuntu.com/fips/ubuntu bionic/main |
      | bionic  | azure.generic | https://esm.ubuntu.com/fips/ubuntu bionic/main |
      | bionic  | gcp.generic   | https://esm.ubuntu.com/fips/ubuntu bionic/main |

  Scenario Outline: FIPS unholds packages
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I apt install `openssh-client openssh-server strongswan`
    And I run `apt-mark hold openssh-client openssh-server strongswan` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
    And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
    And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`
    When I run `pro disable fips --assume-yes` with sudo
    And I run `apt-mark unhold openssh-client openssh-server strongswan` with sudo
    Then I will see the following on stdout:
      """
      openssh-client was already not hold.
      openssh-server was already not hold.
      strongswan was already not hold.
      """
    When I reboot the machine
    Then I verify that `openssh-server` installed version matches regexp `fips`
    And I verify that `openssh-client` installed version matches regexp `fips`
    And I verify that `strongswan` installed version matches regexp `fips`
    And I verify that `strongswan-hmac` installed version matches regexp `fips`

    Examples: ubuntu release
      | release | machine_type  | fips-apt-source                               |
      | focal   | aws.generic   | https://esm.ubuntu.com/fips/ubuntu focal/main |
      | focal   | azure.generic | https://esm.ubuntu.com/fips/ubuntu focal/main |
      | focal   | gcp.generic   | https://esm.ubuntu.com/fips/ubuntu focal/main |

  @slow
  Scenario Outline: Enable FIPS in a cloud VM
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro enable <fips-service> --assume-yes` with sudo
    Then stdout contains substring:
      """
      Updating <fips-name> package lists
      Installing <fips-name> packages
      Updating standard Ubuntu package lists
      <fips-name> enabled
      A reboot is required to complete install
      """
    And I verify that `<fips-service>` is enabled
    And I ensure apt update runs without errors
    And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
    When I run `apt-cache policy <fips-package>` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout matches regexp:
      """
      <fips-kernel>
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """
    And I verify that `<fips-package>` is installed from apt source `<fips-apt-source>`
    When I run `pro disable <fips-service> --assume-yes` with sudo
    Then stdout matches regexp:
      """
      Updating package lists
      """
    When I run `apt-cache policy <fips-package>` as non-root
    Then stdout matches regexp:
      """
      .*Installed: \(none\)
      """
    When I reboot the machine
    Then I verify that `<fips-service>` is disabled

    Examples: ubuntu release
      | release | machine_type  | fips-name    | fips-service | fips-package      | fips-kernel | fips-apt-source                                                |
      | xenial  | azure.generic | FIPS         | fips         | ubuntu-fips       | fips        | https://esm.ubuntu.com/fips/ubuntu xenial/main                 |
      | xenial  | azure.generic | FIPS Updates | fips-updates | ubuntu-fips       | fips        | https://esm.ubuntu.com/fips-updates/ubuntu xenial-updates/main |
      | xenial  | aws.generic   | FIPS         | fips         | ubuntu-fips       | fips        | https://esm.ubuntu.com/fips/ubuntu xenial/main                 |
      | bionic  | azure.generic | FIPS         | fips         | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips/ubuntu bionic/main                 |
      | bionic  | azure.generic | FIPS Updates | fips-updates | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main |
      | bionic  | aws.generic   | FIPS         | fips         | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips/ubuntu bionic/main                 |
      | bionic  | aws.generic   | FIPS Updates | fips-updates | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main |
      | bionic  | gcp.generic   | FIPS         | fips         | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips/ubuntu bionic/main                 |
      | bionic  | gcp.generic   | FIPS Updates | fips-updates | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips-updates/ubuntu bionic-updates/main |
      | focal   | azure.generic | FIPS         | fips         | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips/ubuntu focal/main                  |
      | focal   | azure.generic | FIPS Updates | fips-updates | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main  |
      | focal   | aws.generic   | FIPS         | fips         | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips/ubuntu focal/main                  |
      | focal   | aws.generic   | FIPS Updates | fips-updates | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main  |
      | focal   | gcp.generic   | FIPS         | fips         | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips/ubuntu focal/main                  |
      | focal   | gcp.generic   | FIPS Updates | fips-updates | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips-updates/ubuntu focal-updates/main  |
      | jammy   | azure.generic | FIPS Preview | fips-preview | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips-preview/ubuntu jammy/main          |
      | jammy   | azure.generic | FIPS Updates | fips-updates | ubuntu-azure-fips | azure-fips  | https://esm.ubuntu.com/fips-updates/ubuntu jammy-updates/main  |
      | jammy   | aws.generic   | FIPS Preview | fips-preview | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips-preview/ubuntu jammy/main          |
      | jammy   | aws.generic   | FIPS Updates | fips-updates | ubuntu-aws-fips   | aws-fips    | https://esm.ubuntu.com/fips-updates/ubuntu jammy-updates/main  |
      | jammy   | gcp.generic   | FIPS Preview | fips-preview | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips-preview/ubuntu jammy/main          |
      | jammy   | gcp.generic   | FIPS Updates | fips-updates | ubuntu-gcp-fips   | gcp-fips    | https://esm.ubuntu.com/fips-updates/ubuntu jammy-updates/main  |

  @slow
  Scenario Outline: Attached enable of FIPS in an ubuntu image with cloud-init disabled
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `touch /etc/cloud/cloud-init.disabled` with sudo
    And I reboot the machine
    And I verify that running `cloud-id` `with sudo` exits `1`
    Then stderr matches regexp:
      """
      File not found '/run/cloud-init/instance-data.json'. Provide a path to instance data json file using --instance-data
      """
    When I attach `contract_token` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then stdout contains substring:
      """
      Could not determine cloud, defaulting to generic FIPS package.
      Updating FIPS package lists
      Installing FIPS packages
      Updating standard Ubuntu package lists
      FIPS enabled
      A reboot is required to complete install.
      """
    When I run `apt-cache policy ubuntu-fips` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout does not match regexp:
      """
      aws-fips
      """
    And stdout matches regexp:
      """
      fips
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """

    Examples: ubuntu release
      | release | machine_type |
      | xenial  | aws.generic  |

  @slow
  Scenario Outline: Attached enable of FIPS in an ubuntu image with cloud-init disabled
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `touch /etc/cloud/cloud-init.disabled` with sudo
    And I reboot the machine
    And I verify that running `cloud-id` `with sudo` exits `2`
    Then I will see the following on stdout:
      """
      disabled
      """
    When I attach `contract_token` with sudo
    And I run `pro enable fips --assume-yes` with sudo
    Then stdout matches regexp:
      """
      Could not determine cloud, defaulting to generic FIPS package.
      Updating FIPS package lists
      Installing FIPS packages
      Updating standard Ubuntu package lists
      FIPS enabled
      A reboot is required to complete install.
      """
    When I run `apt-cache policy ubuntu-fips` as non-root
    Then stdout does not match regexp:
      """
      .*Installed: \(none\)
      """
    When I reboot the machine
    And I run `uname -r` as non-root
    Then stdout does not match regexp:
      """
      aws-fips
      """
    And stdout matches regexp:
      """
      fips
      """
    When I run `cat /proc/sys/crypto/fips_enabled` with sudo
    Then I will see the following on stdout:
      """
      1
      """

    Examples: ubuntu release
      | release | machine_type |
      | bionic  | aws.generic  |
      | focal   | aws.generic  |

  Scenario Outline: Attached enable of FIPS in an ubuntu GCP vm
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I verify that running `pro enable fips-updates --assume-yes` `with sudo` exits `1`
    Then stdout matches regexp:
      """
      FIPS Updates is not available for Ubuntu 22.04 LTS \(Jammy Jellyfish\)
      """
    When I run `pro status --all` with sudo
    Then stdout matches regexp:
      """
      fips-updates +yes +n/a
      """

    Examples: ubuntu release
      | release | machine_type  |
      | jammy   | aws.generic   |
      | jammy   | azure.generic |

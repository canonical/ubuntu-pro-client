Feature: Command behaviour when auto-attached in an ubuntu PRO fips image

    @series.lts
    Scenario Outline: Check fips is enabled correctly on Ubuntu pro fips Azure machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        features:
          allow_xenial_fips_on_cloud: true
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        <fips-kernel-version>
        """
        When I run `apt-cache policy ubuntu-azure-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `systemctl daemon-reload` with sudo
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Active: inactive \(dead\).*
        \s*Condition: start condition failed.*
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
        And apt-cache policy for the following url has priority `1001`
        """
        <fips-apt-source> amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        """
        Then stdout matches regexp:
        """
        \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        Installed: .*[~+]esm
        """
        When I run `apt install -y <apps-pkg>/<release>-apps-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <apps-pkg>` as non-root
        Then stdout matches regexp:
        """
        Version table:
        \s*\*\*\* .* 510
        \s*510 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating FIPS Updates package lists
        Installing FIPS Updates packages
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips-updates  +yes +enabled +FIPS compliant crypto packages with stable security updates
        """
        And stdout matches regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """
        When I reboot the machine
        And I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        <fips-kernel-version>
        """
        When I run `apt-cache policy ubuntu-azure-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `pro status` with sudo
        Then stdout does not match regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """

        Examples: ubuntu release
           | release | machine_type   | infra-pkg | apps-pkg | fips-apt-source                                | fips-kernel-version |
           | xenial  | azure.pro-fips | libkrad0  | jq       | https://esm.ubuntu.com/fips/ubuntu xenial/main | fips                |
           | bionic  | azure.pro-fips | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | azure-fips          |
           | focal   | azure.pro-fips | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | azure-fips          |

    @series.focal
    Scenario Outline: Check fips packages are correctly installed on Azure Focal machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | machine_type   | fips-apt-source                                |
           | focal   | azure.pro-fips | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @series.xenial
    @series.bionic
    Scenario Outline: Check fips packages are correctly installed on Azure Bionic & Xenial machines
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        features:
          allow_xenial_fips_on_cloud: true
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | machine_type   | fips-apt-source                                 |
           | xenial  | azure.pro-fips | https://esm.ubuntu.com/fips/ubuntu xenial/main  |
           | bionic  | azure.pro-fips | https://esm.ubuntu.com/fips/ubuntu bionic/main  |

    @series.lts
    Scenario Outline: Check fips is enabled correctly on Ubuntu pro fips AWS machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        <fips-kernel-version>
        """
        When I run `apt-cache policy ubuntu-aws-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `systemctl daemon-reload` with sudo
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Active: inactive \(dead\).*
        \s*Condition: start condition failed.*
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
        And apt-cache policy for the following url has priority `1001`
        """
        <fips-apt-source> amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        """
        Then stdout matches regexp:
        """
        \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        Installed: .*[~+]esm
        """
        When I run `apt install -y <apps-pkg>/<release>-apps-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <apps-pkg>` as non-root
        Then stdout matches regexp:
        """
        Version table:
        \s*\*\*\* .* 510
        \s*510 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating FIPS Updates package lists
        Installing FIPS Updates packages
        Updating standard Ubuntu package lists
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips-updates  +yes +enabled +FIPS compliant crypto packages with stable security updates
        """
        And stdout matches regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """
        When I reboot the machine
        And I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        <fips-kernel-version>
        """
        When I run `apt-cache policy ubuntu-aws-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `pro status` with sudo
        Then stdout does not match regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """

        Examples: ubuntu release
           | release | machine_type | infra-pkg | apps-pkg | fips-apt-source                                | fips-kernel-version |
           | xenial  | aws.pro-fips | libkrad0  | jq       | https://esm.ubuntu.com/fips/ubuntu xenial/main | fips                |
           | bionic  | aws.pro-fips | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | aws-fips            |
           | focal   | aws.pro-fips | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | aws-fips            |

    @series.focal
    Scenario Outline: Check fips packages are correctly installed on AWS Focal machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | machine_type | fips-apt-source                                |
           | focal   | aws.pro-fips | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @series.xenial
    @series.bionic
    Scenario Outline: Check fips packages are correctly installed on AWS Bionic & Xenial machines
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        features:
          allow_xenial_fips_on_cloud: true
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | machine_type | fips-apt-source                                 |
           | xenial  | aws.pro-fips | https://esm.ubuntu.com/fips/ubuntu xenial/main  |
           | bionic  | aws.pro-fips | https://esm.ubuntu.com/fips/ubuntu bionic/main  |

    @series.focal
    Scenario Outline: Check fips-updates can be enabled in a focal PRO FIPS machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then stdout matches regexp:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating FIPS Updates package lists
        Installing FIPS Updates packages
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips-updates  +yes +enabled +FIPS compliant crypto packages with stable security updates
        """
        When I reboot the machine
        And  I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        fips
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """

        Examples: ubuntu release
           | release | machine_type   |
           | focal   | aws.pro-fips   |
           | focal   | azure.pro-fips |
           | focal   | gcp.pro-fips   |

    @series.focal
    @series.bionic
    Scenario Outline: Check fips is enabled correctly on Ubuntu pro fips GCP machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        When I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        <fips-kernel-version>
        """
        When I run `apt-cache policy ubuntu-gcp-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `systemctl daemon-reload` with sudo
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Active: inactive \(dead\).*
        \s*Condition: start condition failed.*
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
        And apt-cache policy for the following url has priority `1001`
        """
        <fips-apt-source> amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        """
        Then stdout matches regexp:
        """
        \s*510 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        Installed: .*[~+]esm
        """
        When I run `apt install -y <apps-pkg>/<release>-apps-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <apps-pkg>` as non-root
        Then stdout matches regexp:
        """
        Version table:
        \s*\*\*\* .* 510
        \s*510 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating FIPS Updates package lists
        Installing FIPS Updates packages
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips-updates  +yes +enabled +FIPS compliant crypto packages with stable security updates
        """
        And stdout matches regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """
        When I reboot the machine
        And I run `uname -r` as non-root
        Then stdout matches regexp:
        """
        <fips-kernel-version>
        """
        When I run `apt-cache policy ubuntu-gcp-fips` as non-root
        Then stdout does not match regexp:
        """
        .*Installed: \(none\)
        """
        When I run `cat /proc/sys/crypto/fips_enabled` with sudo
        Then I will see the following on stdout:
        """
        1
        """
        When I run `pro status` with sudo
        Then stdout does not match regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """

        Examples: ubuntu release
           | release | machine_type | infra-pkg | apps-pkg | fips-apt-source                                | fips-kernel-version |
           | bionic  | gcp.pro-fips | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | gcp-fips            |
           | focal   | gcp.pro-fips | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | gcp-fips            |

    @series.focal
    Scenario Outline: Check fips packages are correctly installed on GCP Pro Focal machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | machine_type | fips-apt-source                                |
           | focal   | gcp.pro-fips | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @series.bionic
    Scenario Outline: Check fips packages are correctly installed on GCP Pro Bionic machines
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --wait` as non-root
        And I run `pro status` as non-root
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified FIPS crypto packages
        fips-updates  +yes +disabled +FIPS compliant crypto packages with stable security updates
        """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-server-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client-hmac` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | machine_type | fips-apt-source                                 |
           | bionic  | gcp.pro-fips | https://esm.ubuntu.com/fips/ubuntu bionic/main  |

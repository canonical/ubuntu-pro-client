Feature: Command behaviour when auto-attached in an ubuntu PRO fips image

    @series.lts
    @uses.config.machine_type.azure.pro.fips
    Scenario Outline: Check fips is enabled correctly on Ubuntu pro fips Azure machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified core packages
        fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
        livepatch     +yes +n/a  +Canonical Livepatch service
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
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Skipping auto-attach: Instance is already attached.
        """
        When I run `pro auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping auto-attach: Instance is already attached.
        """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `1001`
        """
        <fips-apt-source> amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*500 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        \s*500 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
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
        \s*\*\*\* .* 500
        \s*500 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating package lists
        Installing FIPS Updates packages
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips          +yes +n/a +NIST-certified core packages
        fips-updates  +yes +enabled +NIST-certified core packages with priority security updates
        """
        And stdout matches regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """
        When I reboot the `<release>` machine
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
           | release | infra-pkg | apps-pkg | fips-apt-source                                | fips-kernel-version |
           | xenial  | libkrad0  | jq       | https://esm.ubuntu.com/fips/ubuntu xenial/main | fips                |
           | bionic  | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | azure-fips          |
           | focal   | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | azure-fips          |

    @series.focal
    @uses.config.machine_type.azure.pro.fips
    Scenario Outline: Check fips packages are correctly installed on Azure Focal machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +enabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            livepatch     +yes +n/a  +Canonical Livepatch service
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | fips-apt-source                                |
           | focal   | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.azure.pro.fips
    Scenario Outline: Check fips packages are correctly installed on Azure Bionic & Xenial machines
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +enabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            livepatch     +yes +n/a  +Canonical Livepatch service
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
           | release  | fips-apt-source                                 |
           | xenial   | https://esm.ubuntu.com/fips/ubuntu xenial/main  |
           | bionic   | https://esm.ubuntu.com/fips/ubuntu bionic/main  |

    @series.lts
    @uses.config.machine_type.aws.pro.fips
    Scenario Outline: Check fips is enabled correctly on Ubuntu pro fips AWS machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +enabled +NIST-certified core packages
        fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
        livepatch     +yes +n/a  +Canonical Livepatch service
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
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Skipping auto-attach: Instance is already attached.
        """
        When I run `pro auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping auto-attach: Instance is already attached.
        """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `1001`
        """
        <fips-apt-source> amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*500 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        \s*500 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
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
        \s*\*\*\* .* 500
        \s*500 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating package lists
        Installing FIPS Updates packages
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips          +yes +n/a +NIST-certified core packages
        fips-updates  +yes +enabled +NIST-certified core packages with priority security updates
        """
        And stdout matches regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """
        When I reboot the `<release>` machine
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
           | release | infra-pkg | apps-pkg | fips-apt-source                                | fips-kernel-version |
           | xenial  | libkrad0  | jq       | https://esm.ubuntu.com/fips/ubuntu xenial/main | fips                |
           | bionic  | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | aws-fips            |
           | focal   | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | aws-fips            |

    @series.focal
    @uses.config.machine_type.aws.pro.fips
    Scenario Outline: Check fips packages are correctly installed on AWS Focal machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +enabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            livepatch     +yes +n/a  +Canonical Livepatch service
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | fips-apt-source                                |
           | focal   | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.aws.pro.fips
    Scenario Outline: Check fips packages are correctly installed on AWS Bionic & Xenial machines
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +enabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            livepatch     +yes +n/a  +Canonical Livepatch service
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
           | release  | fips-apt-source                                 |
           | xenial   | https://esm.ubuntu.com/fips/ubuntu xenial/main  |
           | bionic   | https://esm.ubuntu.com/fips/ubuntu bionic/main  |

    @series.focal
    @uses.config.machine_type.azure.pro.fips
    @uses.config.machine_type.aws.pro.fips
    @uses.config.machine_type.gcp.pro.fips
    Scenario Outline: Check fips-updates can be enabled in a focal PRO FIPS machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
        fips          +yes +enabled +NIST-certified core packages
        fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then stdout matches regexp:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating package lists
        Installing FIPS Updates packages
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips          +yes +n/a +NIST-certified core packages
        fips-updates  +yes +enabled +NIST-certified core packages with priority security updates
        """
        When I reboot the `<release>` machine
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
           | release  |
           | focal    |

    @series.focal
    @series.bionic
    @uses.config.machine_type.gcp.pro.fips
    Scenario Outline: Check fips is enabled correctly on Ubuntu pro fips GCP machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +enabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            livepatch     +yes +n/a  +Canonical Livepatch service
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
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Skipping auto-attach: Instance is already attached.
        """
        When I run `pro auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping auto-attach: Instance is already attached.
        """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `1001`
        """
        <fips-apt-source> amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*500 https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        \s*500 https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
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
        \s*\*\*\* .* 500
        \s*500 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I run `pro enable fips-updates --assume-yes` with sudo
        Then I will see the following on stdout:
        """
        One moment, checking your subscription first
        Disabling incompatible service: FIPS
        Updating package lists
        Installing FIPS Updates packages
        FIPS Updates enabled
        A reboot is required to complete install.
        """
        When I run `pro status` with sudo
        Then stdout matches regexp:
        """
        fips          +yes +n/a +NIST-certified core packages
        fips-updates  +yes +enabled +NIST-certified core packages with priority security updates
        """
        And stdout matches regexp:
        """
        NOTICES
        FIPS support requires system reboot to complete configuration.
        """
        When I reboot the `<release>` machine
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
           | release | infra-pkg | apps-pkg | fips-apt-source                                | fips-kernel-version |
           | bionic  | libkrad0  | bundler  | https://esm.ubuntu.com/fips/ubuntu bionic/main | gcp-fips            |
           | focal   | hello     | 389-ds   | https://esm.ubuntu.com/fips/ubuntu focal/main  | gcp-fips            |

    @series.focal
    @uses.config.machine_type.gcp.pro.fips
    Scenario Outline: Check fips packages are correctly installed on GCP Pro Focal machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +enabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            livepatch     +yes +n/a  +Canonical Livepatch service
            """
        And I verify that running `apt update` `with sudo` exits `0`
        And I verify that running `grep Traceback /var/log/ubuntu-advantage.log` `with sudo` exits `1`
        And I verify that `openssh-server` is installed from apt source `<fips-apt-source>`
        And I verify that `openssh-client` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan` is installed from apt source `<fips-apt-source>`
        And I verify that `strongswan-hmac` is installed from apt source `<fips-apt-source>`

        Examples: ubuntu release
           | release | fips-apt-source                                |
           | focal   | https://esm.ubuntu.com/fips/ubuntu focal/main  |

    @series.bionic
    @uses.config.machine_type.gcp.pro.fips
    Scenario Outline: Check fips packages are correctly installed on GCP Pro Bionic machines
        Given a `<release>` machine with ubuntu-advantage-tools installed
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
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +enabled +NIST-certified core packages
            fips-updates  +yes +disabled +NIST-certified core packages with priority security updates
            livepatch     +yes +n/a  +Canonical Livepatch service
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
           | release  | fips-apt-source                                 |
           | bionic   | https://esm.ubuntu.com/fips/ubuntu bionic/main  |

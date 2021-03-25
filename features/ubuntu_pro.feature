Feature: Command behaviour when attached to an UA subscription

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.aws.pro
    Scenario Outline: Attached refresh in an Ubuntu PRO machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `ua auto-attach` with sudo
        And I run `ua status --wait` as non-root
        And I run `ua status` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified FIPS modules
            fips-updates  +yes +<fips-s> +Uncertified security updates to FIPS modules
            livepatch     +yes +enabled  +Canonical Livepatch service
            """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            cis           +yes  +<cis-s>  +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified FIPS modules
            fips-updates  +yes +<fips-s> +Uncertified security updates to FIPS modules
            livepatch     +yes +enabled  +Canonical Livepatch service
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
        When I create the file `/var/lib/ubuntu-advantage/marker-reboot-cmds-required` with the following:
        """
        """
        And I reboot the `<release>` machine
        And  I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`

        Then stdout matches regexp:
            """
            .*status=0\/SUCCESS.*
            """

        Examples: ubuntu release
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg |
           | xenial  | disabled | disabled | disabled | libkrad0  | jq       |
           | bionic  | disabled | n/a      | disabled | libkrad0  | bundler  |
           | focal   | n/a      | n/a      | n/a      | hello     | ant      |

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.azure.pro
    Scenario Outline: Attached refresh in an Ubuntu PRO machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `ua auto-attach` with sudo
        And I run `ua status --wait` as non-root
        And I run `ua status` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified FIPS modules
            fips-updates  +yes +<fips-s> +Uncertified security updates to FIPS modules
            livepatch     +yes +enabled  +Canonical Livepatch service
            """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            cis           +yes  +<cis-s>  +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified FIPS modules
            fips-updates  +yes +<fips-s> +Uncertified security updates to FIPS modules
            livepatch     +yes +enabled  +Canonical Livepatch service
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
        When I create the file `/var/lib/ubuntu-advantage/marker-reboot-cmds-required` with the following:
        """
        """
        And I reboot the `<release>` machine
        And  I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`

        Then stdout matches regexp:
            """
            .*status=0\/SUCCESS.*
            """

        Examples: ubuntu release
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg |
           | xenial  | n/a      | disabled | disabled | libkrad0  | jq       |
           | bionic  | disabled | n/a      | disabled | libkrad0  | bundler  |
           | focal   | n/a      | n/a      | n/a      | hello     | ant      |

    @series.xenial
    @series.bionic
    @series.focal
    @uses.config.machine_type.gcp.pro
    Scenario Outline: Attached refresh in an Ubuntu PRO machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `ua auto-attach` with sudo
        And I run `ua status --wait` as non-root
        And I run `ua status` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified FIPS modules
            fips-updates  +yes +<fips-s> +Uncertified security updates to FIPS modules
            livepatch     +yes +enabled  +Canonical Livepatch service
            """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            cis           +yes  +<cis-s>  +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +n/a +NIST-certified FIPS modules
            fips-updates  +yes +n/a +Uncertified security updates to FIPS modules
            livepatch     +yes +enabled  +Canonical Livepatch service
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
        When I create the file `/var/lib/ubuntu-advantage/marker-reboot-cmds-required` with the following:
        """
        """
        And I reboot the `<release>` machine
        And  I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`

        Then stdout matches regexp:
            """
            .*status=0\/SUCCESS.*
            """

        Examples: ubuntu release
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg |
           | xenial  | n/a      | disabled | disabled | libkrad0  | jq       |
           | bionic  | n/a      | n/a      | disabled | libkrad0  | bundler  |
           | focal   | n/a      | n/a      | n/a      | hello     | ant      |

    @series.trusty
    @uses.config.machine_type.aws.pro
    Scenario Outline: Attached refresh in a Trusty Ubuntu PRO machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `-32768`
        """
        https://esm.ubuntu.com/ubuntu/ <release>-infra-updates/main amd64 Packages
        """
        When I run `ua auto-attach` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
            cis           +yes      +n/a    +Center for Internet Security Audit Tools
            esm-apps      +yes      +n/a   +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes      +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes      +n/a   +NIST-certified FIPS modules
            fips-updates  +yes      +n/a   +Uncertified security updates to FIPS modules
            livepatch     +yes      +n/a   +Available with the HWE kernel
            """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/ubuntu/ <release>-infra-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/ubuntu/ <release>-infra-security/main amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*500 https://esm.ubuntu.com/ubuntu/ <release>-infra-security/main amd64 Packages
        \s*500 https://esm.ubuntu.com/ubuntu/ <release>-infra-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        Installed: .*[~+]esm
        """

        Examples: ubuntu release
           | release | infra-pkg   |
           | trusty  | libgit2-dbg |

    @series.trusty
    @uses.config.machine_type.azure.pro
    Scenario Outline: Attached refresh in a Trusty Ubuntu PRO machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `-32768`
        """
        https://esm.ubuntu.com/ubuntu/ <release>-infra-updates/main amd64 Packages
        """
        When I run `ua auto-attach` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
            cis           +yes      +n/a      +Center for Internet Security Audit Tools
            esm-apps      +yes      +n/a   +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes      +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes      +n/a   +NIST-certified FIPS modules
            fips-updates  +yes      +n/a   +Uncertified security updates to FIPS modules
            livepatch     +yes      +disabled   +Canonical Livepatch service
            """
        When I run `apt-cache policy` with sudo
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/ubuntu/ <release>-infra-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.ubuntu.com/ubuntu/ <release>-infra-security/main amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
        Then stdout matches regexp:
        """
        \s*500 https://esm.ubuntu.com/ubuntu/ <release>-infra-security/main amd64 Packages
        \s*500 https://esm.ubuntu.com/ubuntu/ <release>-infra-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        Installed: .*[~+]esm
        """

        Examples: ubuntu release
           | release | infra-pkg   |
           | trusty  | libgit2-dbg |

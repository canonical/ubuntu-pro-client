Feature: Command behaviour when auto-attached in an ubuntu PRO image

    @series.lts
    @uses.config.machine_type.aws.pro
    Scenario Outline: Attached refresh in an Ubuntu pro AWS machine
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
            cis           +yes  +<cis-s>  +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
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
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +enabled  +Canonical Livepatch service
            ros           +no  +(-|—) +Security Updates for the Robot Operating System
            ros-updates   +no  +(-|—) +All Updates for the Robot Operating System
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
           | focal   | n/a      | n/a      | disabled | hello     | ant      |

    @series.lts
    @uses.config.machine_type.azure.pro
    Scenario Outline: Attached refresh in an Ubuntu pro Azure machine
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
            cis           +yes +<cis-s> +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +<livepatch>  +Canonical Livepatch service
            """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            cis           +yes  +<cis-s>  +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +<livepatch>  +Canonical Livepatch service
            ros           +no  +(-|—) +Security Updates for the Robot Operating System
            ros-updates   +no  +(-|—) +All Updates for the Robot Operating System
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
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | livepatch |
           | xenial  | n/a      | disabled | disabled | libkrad0  | jq       | enabled   |
           | bionic  | disabled | n/a      | disabled | libkrad0  | bundler  | n/a       |
           | focal   | n/a      | n/a      | disabled | hello     | ant      | enabled   |

    @series.lts
    @uses.config.machine_type.gcp.pro
    Scenario Outline: Attached refresh in an Ubuntu pro GCP machine
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
            cis           +yes +<cis-s> +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +<livepatch>  +Canonical Livepatch service
            """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            cis           +yes  +<cis-s>  +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes +enabled +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +<livepatch>  +Canonical Livepatch service
            ros           +no  +(-|—) +Security Updates for the Robot Operating System
            ros-updates   +no  +(-|—) +All Updates for the Robot Operating System
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
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | livepatch |
           | xenial  | n/a      | disabled | disabled | libkrad0  | jq       | n/a       |
           | bionic  | disabled | n/a      | disabled | libkrad0  | bundler  | n/a       |
           | focal   | n/a      | n/a      | disabled | hello     | ant      | enabled   |

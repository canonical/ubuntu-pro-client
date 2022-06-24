Feature: Command behaviour when auto-attached in an ubuntu PRO image

    @series.lts
    @uses.config.machine_type.aws.pro
    Scenario Outline: Proxy auto-attach in an Ubuntu pro AWS machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I launch a `focal` `proxy` machine
        And I run `apt install squid -y` `with sudo` on the `proxy` machine
        And I add this text on `/etc/squid/squid.conf` on `proxy` above `http_access deny all`:
            """
            dns_v4_first on\nacl all src 0.0.0.0\/0\nhttp_access allow all
            """
        And I run `systemctl restart squid.service` `with sudo` on the `proxy` machine
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        ua_config:
          http_proxy: http://<ci-proxy-ip>:3128
          https_proxy: http://<ci-proxy-ip>:3128
        """
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        When I run `ua auto-attach` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            """
        Then stdout matches regexp:
            """
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +enabled  +Canonical Livepatch service
            """
        Then stdout matches regexp:
            """
            <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
            """
        When I run `ua enable <cis_or_usg>` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `ua disable <cis_or_usg>` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +disabled   +Security compliance and audit tools
            """
        When I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*CONNECT contracts.canonical.com.*
        """
        And stdout does not match regexp:
        """
        .*CONNECT 169.254.169.254.*
        """
        Examples: ubuntu release
           | release | fips-s   | cc-eal-s | cis-s    | cis_or_usg |
           | xenial  | disabled | disabled | disabled | cis        |
           | bionic  | disabled | disabled | disabled | cis        |
           | focal   | disabled | n/a      | disabled | usg        |

    @series.lts
    @uses.config.machine_type.azure.pro
    Scenario Outline: Proxy auto-attach in an Ubuntu pro Azure machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I launch a `focal` `proxy` machine with ingress ports `3128`
        And I run `apt install squid -y` `with sudo` on the `proxy` machine
        And I add this text on `/etc/squid/squid.conf` on `proxy` above `http_access deny all`:
            """
            dns_v4_first on\nacl all src 0.0.0.0\/0\nhttp_access allow all
            """
        And I run `systemctl restart squid.service` `with sudo` on the `proxy` machine
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        ua_config:
          http_proxy: http://<ci-proxy-ip>:3128
          https_proxy: http://<ci-proxy-ip>:3128
        """
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        When I run `ua auto-attach` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            """
        Then stdout matches regexp:
            """
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +<livepatch-s>  +Canonical Livepatch service
            """
        Then stdout matches regexp:
            """
            <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
            """
        When I run `ua enable <cis_or_usg>` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `ua disable <cis_or_usg>` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +disabled   +Security compliance and audit tools
            """
        When I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*CONNECT contracts.canonical.com.*
        """
        And stdout does not match regexp:
        """
        .*CONNECT 169.254.169.254.*
        """
        Examples: ubuntu release
           | release | fips-s   | cc-eal-s | cis-s    | livepatch-s | cis_or_usg |
           | xenial  | disabled | disabled | disabled | enabled     | cis        |
           | bionic  | disabled | disabled | disabled | enabled     | cis        |
           | focal   | disabled | n/a      | disabled | enabled     | usg        |

    @series.lts
    @uses.config.machine_type.gcp.pro
    Scenario Outline: Proxy auto-attach in an Ubuntu Pro GCP machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I launch a `focal` `proxy` machine
        And I run `apt install squid -y` `with sudo` on the `proxy` machine
        And I add this text on `/etc/squid/squid.conf` on `proxy` above `http_access deny all`:
            """
            dns_v4_first on\nacl all src 0.0.0.0\/0\nhttp_port 3389\nhttp_access allow all
            """
        And I run `systemctl restart squid.service` `with sudo` on the `proxy` machine
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        ua_config:
          http_proxy: http://<ci-proxy-ip>:3389
          https_proxy: http://<ci-proxy-ip>:3389
        """
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        When I run `ua auto-attach` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            """
        Then stdout matches regexp:
            """
            esm-apps      +yes +enabled +Extended Security Maintenance for Applications
            esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
            fips          +yes +<fips-s> +NIST-certified core packages
            fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
            livepatch     +yes +<livepatch-s> +Canonical Livepatch service
            """
        Then stdout matches regexp:
            """
            <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
            """
        When I run `ua enable <cis_or_usg>` with sudo
        And I run `ua status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `ua disable <cis_or_usg>` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `ua status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +disabled   +Security compliance and audit tools
            """
        When I run `cat /var/log/squid/access.log` `with sudo` on the `proxy` machine
        Then stdout matches regexp:
        """
        .*CONNECT contracts.canonical.com.*
        """
        And stdout does not match regexp:
        """
        .*CONNECT metadata.*
        """
        Examples: ubuntu release
           | release | fips-s   | cc-eal-s | cis-s    | livepatch-s | cis_or_usg |
           | xenial  | n/a      | disabled | disabled | n/a         | cis        |
           | bionic  | disabled | disabled | disabled | enabled     | cis        |
           | focal   | disabled | n/a      | disabled | enabled     | usg        |

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
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified core packages
        fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
        livepatch     +yes +enabled  +Canonical Livepatch service
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified core packages
        fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
        livepatch     +yes +enabled  +Canonical Livepatch service
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
        """
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Skipping attach: Instance '[0-9a-z\-]+' is already attached.
        """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping attach: Instance '[0-9a-z\-]+' is already attached.
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
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | cis_or_usg |
           | xenial  | disabled | disabled | disabled | libkrad0  | jq       | cis        |
           | bionic  | disabled | disabled | disabled | libkrad0  | bundler  | cis        |
           | focal   | disabled | n/a      | disabled | hello     | ant      | usg        |
           | jammy   | n/a      | n/a      | n/a      | hello     | hello    | usg        |


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
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified core packages
        fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
        livepatch     +yes +<livepatch>  +Canonical Livepatch service
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes +<cis-s> +Security compliance and audit tools
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE      +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified core packages
        fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
        livepatch     +yes +<livepatch>  +Canonical Livepatch service
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
        """
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Skipping attach: Instance '[0-9a-z\-]+' is already attached.
        """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping attach: Instance '[0-9a-z\-]+' is already attached.
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
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | livepatch | cis_or_usg |
           | xenial  | disabled | disabled | disabled | libkrad0  | jq       | enabled   | cis        |
           | bionic  | disabled | disabled | disabled | libkrad0  | bundler  | enabled   | cis        |
           | focal   | disabled | n/a      | disabled | hello     | ant      | enabled   | usg        |
           | jammy   | n/a      | n/a      | n/a      | hello     | hello    | enabled   | usg        |

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
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified core packages
        fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
        livepatch     +yes +<livepatch>  +Canonical Livepatch service
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes +<cis-s> +Security compliance and audit tools
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Extended Security Maintenance for Applications
        esm-infra     +yes +enabled +Extended Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified core packages
        fips-updates  +yes +<fips-s> +NIST-certified core packages with priority security updates
        livepatch     +yes +<livepatch>  +Canonical Livepatch service
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
        """
        When I run `systemctl start ua-auto-attach.service` with sudo
        And I verify that running `systemctl status ua-auto-attach.service` `as non-root` exits `0,3`
        Then stdout matches regexp:
        """
        .*status=0\/SUCCESS.*
        """
        And stdout matches regexp:
        """
        Skipping attach: Instance '[0-9a-z\-]+' is already attached.
        """
        When I run `ua auto-attach` with sudo
        Then stderr matches regexp:
        """
        Skipping attach: Instance '[0-9a-z\-]+' is already attached.
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
           | release | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | livepatch | cis_or_usg |
           | xenial  | n/a      | disabled | disabled | libkrad0  | jq       | n/a       | cis        |
           | bionic  | disabled | disabled | disabled | libkrad0  | bundler  | enabled   | cis        |
           | focal   | disabled | n/a      | disabled | hello     | ant      | enabled   | usg        |
           | jammy   | n/a      | n/a      | n/a      | hello     | hello    | enabled   | usg        |

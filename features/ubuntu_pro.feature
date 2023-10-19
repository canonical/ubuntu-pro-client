Feature: Command behaviour when auto-attached in an ubuntu PRO image

    Scenario Outline: Proxy auto-attach in an Ubuntu pro AWS machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        Given a `focal` `<machine_type>` machine named `proxy`
        When I run `apt install squid -y` `with sudo` on the `proxy` machine
        And I add this text on `/etc/squid/squid.conf` on `proxy` above `http_access deny all`:
            """
            dns_v4_first on\nacl all src 0.0.0.0\/0\nhttp_access allow all
            """
        And I run `systemctl restart squid.service` `with sudo` on the `proxy` machine
        # This also tests that legacy `ua_config` settings still work
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        ua_config:
          http_proxy: http://$behave_var{machine-ip proxy}:3128
          https_proxy: http://$behave_var{machine-ip proxy}:3128
        """
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        When I run `pro auto-attach` with sudo
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +ENTITLED  STATUS    DESCRIPTION
            anbox-cloud   +(yes|no)  .*
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            """
        Then stdout matches regexp:
            """
            esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
            esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
            fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
            fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
            livepatch     +yes +enabled  +Canonical Livepatch service
            """
        Then stdout matches regexp:
            """
            <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
            """
        When I run `pro enable <cis_or_usg>` with sudo
        And I run `pro status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `pro disable <cis_or_usg>` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `pro status` with sudo
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
           | release | machine_type | fips-s   | cc-eal-s | cis-s    | cis_or_usg |
           | xenial  | aws.pro      | disabled | disabled | disabled | cis        |
           | bionic  | aws.pro      | disabled | disabled | disabled | cis        |
           | focal   | aws.pro      | disabled | n/a      | disabled | usg        |

    Scenario Outline: Proxy auto-attach in an Ubuntu pro Azure machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        Given a `focal` `<machine_type>` machine named `proxy` with ingress ports `3128`
        When I run `apt install squid -y` `with sudo` on the `proxy` machine
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
          http_proxy: http://$behave_var{machine-ip proxy}:3128
          https_proxy: http://$behave_var{machine-ip proxy}:3128
        """
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        When I run `pro auto-attach` with sudo
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +ENTITLED  STATUS    DESCRIPTION
            anbox-cloud   +(yes|no)  .*
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            """
        Then stdout matches regexp:
            """
            esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
            esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
            fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
            fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
            livepatch     +yes +<livepatch-s>  +Canonical Livepatch service
            """
        Then stdout matches regexp:
            """
            <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
            """
        When I run `pro enable <cis_or_usg>` with sudo
        And I run `pro status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `pro disable <cis_or_usg>` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `pro status` with sudo
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
           | release | machine_type | fips-s   | cc-eal-s | cis-s    | livepatch-s | cis_or_usg |
           | xenial  | azure.pro    | disabled | disabled | disabled | enabled     | cis        |
           | bionic  | azure.pro    | disabled | disabled | disabled | enabled     | cis        |
           | focal   | azure.pro    | disabled | n/a      | disabled | enabled     | usg        |

    Scenario Outline: Proxy auto-attach in an Ubuntu Pro GCP machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        Given a `focal` `<machine_type>` machine named `proxy`
        When I run `apt install squid -y` `with sudo` on the `proxy` machine
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
          http_proxy: http://$behave_var{machine-ip proxy}:3389
          https_proxy: http://$behave_var{machine-ip proxy}:3389
        """
        And I verify `/var/log/squid/access.log` is empty on `proxy` machine
        When I run `pro auto-attach` with sudo
        When I run `pro status --all` with sudo
        Then stdout matches regexp:
            """
            SERVICE       +ENTITLED  STATUS    DESCRIPTION
            anbox-cloud   +(yes|no)  .*
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            """
        Then stdout matches regexp:
            """
            esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
            esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
            fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
            fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
            livepatch     +yes +<livepatch-s> +<lp-desc>
            """
        Then stdout matches regexp:
            """
            <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
            """
        When I run `pro enable <cis_or_usg>` with sudo
        And I run `pro status` with sudo
        Then stdout matches regexp:
            """
            <cis_or_usg>         +yes    +enabled   +Security compliance and audit tools
            """
        When I run `pro disable <cis_or_usg>` with sudo
        Then stdout matches regexp:
            """
            Updating package lists
            """
        When I run `pro status` with sudo
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
           | release | machine_type | fips-s   | cc-eal-s | cis-s    | livepatch-s | lp-desc                         | cis_or_usg |
           | xenial  | gcp.pro      | n/a      | disabled | disabled | warning     | Current kernel is not supported | cis        |
           | bionic  | gcp.pro      | disabled | disabled | disabled | enabled     | Canonical Livepatch service     | cis        |
           | focal   | gcp.pro      | disabled | n/a      | disabled | enabled     | Canonical Livepatch service     | usg        |

    Scenario Outline: Attached refresh in an Ubuntu pro AWS machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --all --wait` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        anbox-cloud   +(yes|no)  .*
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
        fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
        livepatch     +yes +<livepatch-s>  +(Canonical Livepatch service|Current kernel is not supported)
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes  +<cis-s>  +Security compliance and audit tools
        """
        When I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        anbox-cloud   +(yes|no)  .*
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
        fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
        livepatch     +yes +<livepatch-s>  +(Canonical Livepatch service|Current kernel is not supported)
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
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
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
        When I create the file `/var/lib/ubuntu-advantage/marker-reboot-cmds-required` with the following:
        """
        """
        And I reboot the machine
        And  I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`
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
           | release | machine_type | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | cis_or_usg | livepatch-s |
           | xenial  | aws.pro      | disabled | disabled | disabled | libkrad0  | jq       | cis        | enabled     |
           | bionic  | aws.pro      | disabled | disabled | disabled | libkrad0  | bundler  | cis        | enabled     |
           | focal   | aws.pro      | disabled | n/a      | disabled | hello     | ant      | usg        | enabled     |
           | jammy   | aws.pro      | n/a      | n/a      | disabled | hello     | hello    | usg        | warning     |


    Scenario Outline: Attached refresh in an Ubuntu pro Azure machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --all --wait` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        anbox-cloud   +(yes|no)  .*
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
        fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
        livepatch     +yes +<livepatch>  +Canonical Livepatch service
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes +<cis-s> +Security compliance and audit tools
        """
        When I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE      +ENTITLED  STATUS    DESCRIPTION
        anbox-cloud   +(yes|no)  .*
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
        fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
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
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
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
        When I create the file `/var/lib/ubuntu-advantage/marker-reboot-cmds-required` with the following:
        """
        """
        And I reboot the machine
        And  I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`
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
           | release | machine_type | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | livepatch | cis_or_usg |
           | xenial  | azure.pro    | disabled | disabled | disabled | libkrad0  | jq       | enabled   | cis        |
           | bionic  | azure.pro    | disabled | disabled | disabled | libkrad0  | bundler  | enabled   | cis        |
           | focal   | azure.pro    | disabled | n/a      | disabled | hello     | ant      | enabled   | usg        |
           | jammy   | azure.pro    | n/a      | n/a      | disabled | hello     | hello    | enabled   | usg        |

    Scenario Outline: Attached refresh in an Ubuntu pro GCP machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I run `pro auto-attach` with sudo
        And I run `pro status --all --wait` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        anbox-cloud   +(yes|no)  .*
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
        fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
        livepatch     +yes +<livepatch>  +<lp-desc>
        """
        Then stdout matches regexp:
        """
        <cis_or_usg>           +yes +<cis-s> +Security compliance and audit tools
        """
        When I run `pro status --all` as non-root
        Then stdout matches regexp:
        """
        SERVICE       +ENTITLED  STATUS    DESCRIPTION
        anbox-cloud   +(yes|no)  .*
        cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
        """
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        fips          +yes +<fips-s> +NIST-certified FIPS crypto packages
        fips-updates  +yes +<fips-s> +FIPS compliant crypto packages with stable security updates
        livepatch     +yes +<livepatch>  +<lp-desc>
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
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo, retrying exit [100]
        And I run `apt-cache policy <infra-pkg>` as non-root
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
        When I create the file `/var/lib/ubuntu-advantage/marker-reboot-cmds-required` with the following:
        """
        """
        And I reboot the machine
        And  I verify that running `systemctl status ua-reboot-cmds.service` `as non-root` exits `0,3`
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
           | release | machine_type | fips-s   | cc-eal-s | cis-s    | infra-pkg | apps-pkg | livepatch | lp-desc                         | cis_or_usg |
           | xenial  | gcp.pro      | n/a      | disabled | disabled | libkrad0  | jq       | warning   | Current kernel is not supported | cis        |
           | bionic  | gcp.pro      | disabled | disabled | disabled | libkrad0  | bundler  | enabled   | Canonical Livepatch service     | cis        |
           | focal   | gcp.pro      | disabled | n/a      | disabled | hello     | ant      | enabled   | Canonical Livepatch service     | usg        |
           | jammy   | gcp.pro      | n/a      | n/a      | disabled | hello     | hello    | enabled   | Canonical Livepatch service     | usg        |

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

    Scenario Outline: Auto-attach no-op when cloud-init has ubuntu_advantage on userdata
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed adding this cloud-init user_data:
        # This user_data should not do anything, just guarantee that the ua-auto-attach service
        # does nothing
        """
        ubuntu_advantage:
          features:
            disable_auto_attach: true
        """
        When I run `cloud-init query userdata` with sudo
        Then stdout matches regexp:
        """
        ubuntu_advantage:
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
        When I run `cat /var/log/ubuntu-advantage.log` with sudo
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

    Scenario Outline: Unregistered Pro machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I verify that running `pro auto-attach` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        Error on Pro Image:
        missing instance information
        """

        Examples: ubuntu release
           | release | machine_type |
           | xenial  | aws.generic  |
           | bionic  | aws.generic  |
           | focal   | aws.generic  |
           | jammy   | aws.generic  |

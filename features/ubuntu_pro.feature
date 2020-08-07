@uses.config.machine_type.pro.azure
@uses.config.machine_type.pro.aws
Feature: Command behaviour when attached to an UA subscription

    @series.xenial
    @series.bionic
    @series.focal
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
        And I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +<cc-eal> +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            cis-audit     +no       +—    +Center for Internet Security Audit Tools
            esm-apps      +yes +enabled +UA Apps: Extended Security Maintenance
            esm-infra     +yes     +enabled +UA Infra: Extended Security Maintenance
            fips          +<fips> +<fips-s> +NIST-certified FIPS modules
            fips-updates  +<fips> +<fips-s> +Uncertified security updates to FIPS modules
            livepatch     +yes      +enabled  +Canonical Livepatch service
            """
        When I run `apt-cache policy` with sudo
        Then stdout matches regexp:
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        https://esm.ubuntu.com/infra/ubuntu <release>-infra-security/main amd64 Packages
        """
        And stdout matches regexp:
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
        """
        And stdout matches regexp:
        """
        https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        And I verify that running `apt update` as `sudo` succeeds
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo
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
        When I run `apt install -y <apps-pkg>/<release>-apps-security` with sudo
        And I run `apt-cache policy <apps-pkg>` as non-root
        Then stdout matches regexp:
        """
        Version table:
        \s*\*\*\* .* 500
        \s*500 https://esm.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """

        Examples: ubuntu release
           | release | cc-eal | cc-eal-s | fips | fips-s | infra-pkg    | apps-pkg |
           | xenial  | yes    | disabled | yes  | n/a    | libkrad0     | jq       |
           | bionic  | yes    | n/a      | yes  | n/a    | libkrad0     | bundler  |
           | focal   | yes    | n/a      | yes  | n/a    | hello        | ant      |

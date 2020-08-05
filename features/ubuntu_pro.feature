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
        Examples: ubuntu release
           | release | cc-eal | cc-eal-s | fips | fips-s |
           | xenial  | yes    | disabled | yes  | n/a    |
           | bionic  | yes    | n/a      | yes  | n/a    |
           | focal   | yes    | n/a      | yes  | n/a    |

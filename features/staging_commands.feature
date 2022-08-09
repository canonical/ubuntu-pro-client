@uses.config.contract_token_staging
Feature: Enable command behaviour when attached to an Ubuntu Pro staging subscription

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable esm-apps on a machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo
        And I run `pro status --all` as non-root
        Then stdout matches regexp
        """
        esm-apps      +yes                enabled            Extended Security Maintenance for Applications
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt-cache policy` as non-root
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.staging.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.staging.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <apps-pkg>` with sudo, retrying exit [100]
        And I run `apt-cache policy <apps-pkg>` as non-root
        Then stdout matches regexp:
        """
        Version table:
        \s*\*\*\* .* 500
        \s*500 https://esm.staging.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I verify that running `pro enable esm-apps` `with sudo` exits `1`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        Ubuntu Pro: ESM Apps is already enabled.
        See: sudo pro status
        """

        Examples: ubuntu release
           | release | apps-pkg |
           | xenial  | jq       |
           | bionic  | bundler  |
           | focal   | ant      |

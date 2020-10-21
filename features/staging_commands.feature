@uses.config.contract_token_staging
Feature: Enable command behaviour when attached to an UA staging subscription

    @series.xenial
    Scenario: Attached enable CC EAL service in a xenial lxd container
        Given a `xenial` machine with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo
        And I run `ua enable cc-eal` as non-root
        Then I will see the following on stderr:
            """
            This command must be run as root (try using sudo)
            """
        When I run `ua enable cc-eal --beta` with sudo
        Then I will see the following on stdout:
            """
            One moment, checking your subscription first
            GPG key '/usr/share/keyrings/ubuntu-cc-keyring.gpg' not found
            """

    @series.xenial
    @series.bionic
    @series.focal
    Scenario Outline: Attached enable esm-apps on a machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        esm-infra     no                 —                  UA Infra: Extended Security Maintenance \(ESM\)
        livepatch     yes                n/a                Canonical Livepatch service
        """
        When I run `ua disable livepatch` with sudo
        Then I verify that running `apt update` `with sudo` exits `0`
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
        When I run `apt install -y <apps-pkg>` with sudo
        And I run `apt-cache policy <apps-pkg>` as non-root
        Then stdout matches regexp:
        """
        Version table:
        \s*\*\*\* .* 500
        \s*500 https://esm.staging.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """

        Examples: ubuntu release
           | release | apps-pkg |
           | bionic  | bundler  |
           | focal   | ant      |
           | trusty  | ant      |
           | xenial  | jq       |

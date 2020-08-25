@uses.config.machine_type.azure.pro
@uses.config.machine_type.aws.pro
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
            cc-eal        +yes +<cc-eal-s>  +Common Criteria EAL2 Provisioning Packages
            cis-audit     +no       +—    +Center for Internet Security Audit Tools
            esm-apps      +yes +<esm-a-s> +UA Apps: Extended Security Maintenance
            esm-infra     +yes     +enabled +UA Infra: Extended Security Maintenance
            fips          +yes +<fips-s> +NIST-certified FIPS modules
            fips-updates  +yes +<fips-s> +Uncertified security updates to FIPS modules
            livepatch     +yes      +<lp-s>  +<lp-d>
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

        # focal livepatch status is displayed was disabled because livepatch
        # currently fails to apply the kernel patches on the aws focal pro kernel version.
        # We are changing the status to disabled just to unlock the build, but we
        # need a better fix for that issue.
        Examples: ubuntu release
           | release | cc-eal-s | esm-a-s | infra-pkg | apps-pkg | fips-s | lp-s     | lp-d                          |
           | xenial  | disabled | enabled | libkrad0  | jq       | n/a    | enabled  | Canonical Livepatch service |
           | bionic  | n/a      | enabled | libkrad0  | bundler  | n/a    | enabled  | Canonical Livepatch service |
           | focal   | n/a      | enabled | hello     | ant      | n/a    | disabled | Canonical Livepatch service |

    @series.trusty
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
            cis-audit     +no       +—    +Center for Internet Security Audit Tools
            esm-apps      +yes      +n/a   +UA Apps: Extended Security Maintenance
            esm-infra     +yes      +enabled +UA Infra: Extended Security Maintenance
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
        When I run `apt install -y <infra-pkg>/<release>-infra-security` with sudo
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

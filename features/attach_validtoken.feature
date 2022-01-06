@uses.config.contract_token
Feature: Command behaviour when attaching a machine to an Ubuntu Advantage
        subscription using a valid token

    @series.jammy
    @series.hirsute
    @series.impish
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached command in a non-lts ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp:
            """
            SERVICE       ENTITLED  STATUS    DESCRIPTION
            cc-eal        +yes      +n/a      +Common Criteria EAL2 Provisioning Packages
            cis           +yes      +n/a      +Security compliance and audit tools
            esm-apps      +yes      +n/a      +UA Apps: Extended Security Maintenance \(ESM\)
            esm-infra     +yes      +n/a      +UA Infra: Extended Security Maintenance \(ESM\)
            fips          +yes      +n/a      +NIST-certified core packages
            fips-updates  +yes      +n/a      +NIST-certified core packages with priority security updates
            livepatch     +yes      +n/a      +Canonical Livepatch service
            """

        Examples: ubuntu release
            | release |
            | hirsute |
            | impish  |
            | jammy   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attach command in a ubuntu lxd container
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo, retrying exit [100]
        And I run `DEBIAN_FRONTEND=noninteractive apt-get install -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" -y <downrev_pkg>` with sudo, retrying exit [100]
        And I run `run-parts /etc/update-motd.d/` with sudo
        Then if `<release>` in `xenial` and stdout matches regexp:
        """
        \d+ update(s)? can be applied immediately.
        \d+ of these updates (is a|are) standard security update(s)?.
        """
        Then if `<release>` in `bionic` and stdout matches regexp:
        """
        \d+ update(s)? can be applied immediately.
        \d+ of these updates (is a|are) standard security update(s)?.
        """
        Then if `<release>` in `focal` and stdout matches regexp:
        """
        \d+ update(s)? can be applied immediately.
        """
        When I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        UA Infra: ESM enabled
        """
        And stdout matches regexp:
        """
        This machine is now attached to
        """
        And stdout matches regexp:
        """
        SERVICE       ENTITLED  STATUS    DESCRIPTION
        cc-eal       +yes      +<cc_status>     +Common Criteria EAL2 Provisioning Packages
        """
        And stdout matches regexp:
        """
        esm-apps     +yes      +enabled  +UA Apps: Extended Security Maintenance \(ESM\)
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +n/a      +NIST-certified core packages
        fips-updates +yes      +n/a      +NIST-certified core packages with priority security updates
        livepatch    +yes      +n/a      +Canonical Livepatch service
        """
        And stdout matches regexp:
        """
        <cis_or_usg> +yes      +disabled        +Security compliance and audit tools
        """
        And stderr matches regexp:
        """
        Enabling default service esm-infra
        """
        When I verify that running `ua attach contract_token` `with sudo` exits `2`
        Then stderr matches regexp:
        """
        This machine is already attached to '.+'
        To use a different subscription first run: sudo ua detach.
        """
        When I run `ua disable esm-apps --assume-yes` with sudo
        When I append the following on uaclient config:
            """
            features:
              allow_beta: true
            """
        And I run `apt update` with sudo
        And I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `apt install update-motd` with sudo, retrying exit [100]
        And I run `update-motd` with sudo
        Then if `<release>` in `focal` and stdout matches regexp:
        """
        \* Introducing Extended Security Maintenance for Applications.
          +Receive updates to over 30,000 software packages with your
          +Ubuntu Advantage subscription. Free for personal use.

            +https:\/\/ubuntu.com\/esm

        \d+ update(s)? can be applied immediately.
        \d+ of these updates (is|are) (a|an)? UA Infra: ESM security update(s)?.
        (\d+ of these updates (is a|are) standard security update(s)?.)?
        ?To see these additional updates run: apt list --upgradable
        """
        Then if `<release>` in `bionic` and stdout matches regexp:
        """
        \* Introducing Extended Security Maintenance for Applications.
          +Receive updates to over 30,000 software packages with your
          +Ubuntu Advantage subscription. Free for personal use.

            +https:\/\/ubuntu.com\/esm

        \d+ update(s)? can be applied immediately.
        \d+ of these updates (is a|are) standard security update(s)?.
        To see these additional updates run: apt list --upgradable
        """
        Then if `<release>` in `xenial` and stdout matches regexp:
        """
        \* Introducing Extended Security Maintenance for Applications.
          +Receive updates to over 30,000 software packages with your
          +Ubuntu Advantage subscription. Free for personal use.

            +https:\/\/ubuntu.com\/16-04

        UA Infra: Extended Security Maintenance \(ESM\) is enabled.

        \d+ update(s)? can be applied immediately.
        \d+ of these updates (is|are) UA Infra: ESM security update(s)?.
        \d+ of these updates (is a|are) standard security update(s)?.
        To see these additional updates run: apt list --upgradable
        """
        When I update contract to use `effectiveTo` as `days=-20`
        And I delete the file `/var/lib/ubuntu-advantage/jobs-status.json`
        And I run `python3 /usr/lib/ubuntu-advantage/timer.py` with sudo
        And I run `update-motd` with sudo
        Then if `<release>` in `xenial` and stdout matches regexp:
        """

        \*Your UA Infra: ESM subscription has EXPIRED\*

        \d+ additional security update\(s\) could have been applied via UA Infra: ESM.

        Renew your UA services at https:\/\/ubuntu.com\/advantage

        """
        Then if `<release>` in `xenial` and stdout matches regexp:
        """

        Ubuntu comes with ABSOLUTELY NO WARRANTY, to the extent permitted by
        applicable law.

        """
        When I run `apt upgrade --dry-run` with sudo
        Then if `<release>` in `xenial` and stdout matches regexp:
        """
        \*Your UA Infra: ESM subscription has EXPIRED\*
        Enabling UA Infra: ESM service would provide security updates for following packages:
          .*
        \d+ esm-infra security update\(s\) NOT APPLIED. Renew your UA services at
        https:\/\/ubuntu.com\/advantage

        """
        Examples: ubuntu release packages
           | release | downrev_pkg                 | cc_status | cis_or_usg |
           | xenial  | libkrad0=1.13.2+dfsg-5      | disabled  | cis        |
           | bionic  | libkrad0=1.16-2build1       | n/a       | cis        |
           | focal   | hello=2.10-2ubuntu2         | n/a       | usg        |

    @series.all
    @uses.config.machine_type.aws.generic
    Scenario Outline: Attach command in an generic AWS Ubuntu VM
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "esm-apps",
                            "entitled": false
                        }
                    ]
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
        """
        And I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        UA Infra: ESM enabled
        """
        And stdout matches regexp:
        """
        This machine is now attached to
        """
        And stdout matches regexp:
        """
        SERVICE       ENTITLED  STATUS    DESCRIPTION
        cc-eal       +yes      +<cc_status>     +Common Criteria EAL2 Provisioning Packages
        """
        And stdout matches regexp:
        """
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +<fips_status>      +NIST-certified core packages
        fips-updates +yes      +<fips_status>      +NIST-certified core packages with priority security updates
        livepatch    +yes      +<lp_status>  +<lp_desc>
        """
        And stdout matches regexp:
        """
        <cis_or_usg>          +yes      +disabled +Security compliance and audit tools
        """
        And stderr matches regexp:
        """
        Enabling default service esm-infra
        """

        Examples: ubuntu release livepatch status
           | release | fips_status |lp_status | lp_desc                       | cc_status | cis_or_usg |
           | xenial  | disabled    |enabled   | Canonical Livepatch service   | disabled  | cis        |
           | bionic  | disabled    |enabled   | Canonical Livepatch service   | n/a       | cis        |
           | focal   | n/a         |enabled   | Canonical Livepatch service   | n/a       | usg        |

    @series.all
    @uses.config.machine_type.azure.generic
    Scenario Outline: Attach command in an generic Azure Ubuntu VM
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "esm-apps",
                            "entitled": false
                        }
                    ]
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
        """
        And I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        UA Infra: ESM enabled
        """
        And stdout matches regexp:
        """
        This machine is now attached to
        """
        And stdout matches regexp:
        """
        SERVICE       ENTITLED  STATUS    DESCRIPTION
        cc-eal       +yes      +<cc_status>     +Common Criteria EAL2 Provisioning Packages
        """
        And stdout matches regexp:
        """
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +<fips_status> +NIST-certified core packages
        fips-updates +yes      +<fips_status> +NIST-certified core packages with priority security updates
        livepatch    +yes      +<lp_status>  +Canonical Livepatch service
        """
        And stdout matches regexp:
        """
        <cis_or_usg>          +yes      +disabled +Security compliance and audit tools
        """
        And stderr matches regexp:
        """
        Enabling default service esm-infra
        """

        Examples: ubuntu release livepatch status
           | release | lp_status | fips_status | cc_status | cis_or_usg |
           | xenial  | n/a       | n/a         | disabled  | cis        |
           | bionic  | n/a       | disabled    | n/a       | cis        |
           | focal   | enabled   | n/a         | n/a       | usg        |

    @series.all
    @uses.config.machine_type.gcp.generic
    Scenario Outline: Attach command in an generic GCP Ubuntu VM
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/tmp/machine-token-overlay.json` with the following:
        """
        {
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {
                            "type": "esm-apps",
                            "entitled": false
                        }
                    ]
                }
            }
        }
        """
        And I append the following on uaclient config:
        """
        features:
          machine_token_overlay: "/tmp/machine-token-overlay.json"
        """
        And I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        UA Infra: ESM enabled
        """
        And stdout matches regexp:
        """
        This machine is now attached to
        """
        And stdout matches regexp:
        """
        SERVICE       ENTITLED  STATUS    DESCRIPTION
        cc-eal       +yes      +<cc_status>     +Common Criteria EAL2 Provisioning Packages
        """
        And stdout matches regexp:
        """
        esm-infra    +yes      +enabled  +UA Infra: Extended Security Maintenance \(ESM\)
        fips         +yes      +<fips_status> +NIST-certified core packages
        fips-updates +yes      +<fips_status> +NIST-certified core packages with priority security updates
        livepatch    +yes      +<lp_status>  +Canonical Livepatch service
        """
        And stdout matches regexp:
        """
        <cis_or_usg>          +yes      +disabled +Security compliance and audit tools
        """
        And stderr matches regexp:
        """
        Enabling default service esm-infra
        """

        Examples: ubuntu release livepatch status
           | release | lp_status | fips_status | cc_status | cis_or_usg |
           | xenial  | n/a       | n/a         | disabled  | cis        |
           | bionic  | n/a       | disabled    | n/a       | cis        |
           | focal   | enabled   | n/a         | n/a       | usg        |

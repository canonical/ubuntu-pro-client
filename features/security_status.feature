Feature: Security status command behavior

    @uses.config.contract_token
    Scenario Outline: Run security status with JSON/YAML format
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        And I run `apt-get install ansible -y` with sudo
        And I run `pro security-status --format json` as non-root
        Then stdout is a json matching the `ua_security_status` schema
        And stdout matches regexp:
        """
        "_schema_version": "0.1"
        """
        And stdout matches regexp:
        """
        "attached": false
        """
        And stdout matches regexp:
        """
        "enabled_services": \[\]
        """
        And stdout matches regexp:
        """
        "entitled_services": \[\]
        """
        And stdout matches regexp:
        """
        "package": "<package>"
        """
        And stdout matches regexp:
        """
        "service_name": "<service>"
        """
        And stdout matches regexp:
        """
        "origin": "esm.ubuntu.com"
        """
        And stdout matches regexp:
        """
        "status": "pending_attach"
        """
        And stdout matches regexp:
        """
        "download_size": \d+
        """
        When I attach `contract_token` with sudo
        And I run `pro security-status --format json` as non-root
        Then stdout is a json matching the `ua_security_status` schema
        Then stdout matches regexp:
        """
        "_schema_version": "0.1"
        """
        And stdout matches regexp:
        """
        "attached": true
        """
        And stdout matches regexp:
        """
        "enabled_services": \["esm-apps", "esm-infra"\]
        """
        And stdout matches regexp:
        """
        "entitled_services": \["esm-apps", "esm-infra"\]
        """
        And stdout matches regexp:
        """
        "status": "upgrade_available"
        """
        And stdout matches regexp:
        """
        "download_size": \d+
        """
        When I run `pro security-status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_security_status` schema
        And stdout matches regexp:
        """
        _schema_version: '0.1'
        """
        When I verify that running `pro security-status --format unsupported` `as non-root` exits `2`
        Then I will see the following on stderr:
        """
        usage: security-status [-h] [--format {json,yaml,text}]
                               [--thirdparty | --unavailable | --esm-infra | --esm-apps]
        argument --format: invalid choice: 'unsupported' (choose from 'json', 'yaml', 'text')
        """
        Examples: ubuntu release
           | release | machine_type  | package   | service   |
           | xenial  | lxd-container | apport    | esm-infra |
           | bionic  | lxd-container | ansible   | esm-apps  |

    @uses.config.contract_token
    Scenario: Check for livepatch CVEs in security-status on an Ubuntu machine
        Given a `xenial` `lxd-vm` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `pro security-status --format json` as non-root
        Then stdout is a json matching the `ua_security_status` schema
        Then stdout matches regexp:
        """
        {"name": "cve-2013-1798", "patched": true}
        """
        When I run `pro security-status --format yaml` as non-root
        Then stdout is a yaml matching the `ua_security_status` schema
        And stdout matches regexp:
        """
          - name: cve-2013-1798
            patched: true
        """

    @uses.config.contract_token
    Scenario: Run security status in an Ubuntu machine
        Given a `xenial` `lxd-container` machine with ubuntu-advantage-tools installed
        When I install third-party / unknown packages in the machine
        # Ansible is in esm-apps
        And I run `apt-get install -y ansible` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is NOT receiving security patches because the LTS period has ended
        and esm-infra is not enabled.
        This machine is NOT attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026\. There (is|are) \d+ pending security update[s]?\.

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026\. There (is|are) \d+ pending security update[s]?\.

        Try Ubuntu Pro with a free personal subscription on up to 5 machines.
        Learn more at https://ubuntu.com/pro
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository

        This machine is NOT receiving security patches because the LTS period has ended
        and esm-infra is not enabled.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026\. There (is|are) \d+ pending security update[s]?\.

        Run 'pro help esm-infra' to learn more

        Installed packages with an available esm-infra update:
        (.|\n)+

        Further installed packages covered by esm-infra:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026\. There (is|are) \d+ pending security update[s]?\.

        Run 'pro help esm-apps' to learn more

        Installed packages with an available esm-apps update:
        (.|\n)+

        Further installed packages covered by esm-apps:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I attach `contract_token` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is attached to an Ubuntu Pro subscription.

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2026\. There (is|are) \d+ pending security update[s]?\.

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2026\. There (is|are) \d+ pending security update[s]?\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2026\. There (is|are) \d+ pending security update[s]?\.

        Run 'pro help esm-infra' to learn more

        Installed packages with an available esm-infra update:
        (.|\n)+

        Further installed packages covered by esm-infra:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2026\. There (is|are) \d+ pending security update[s]?\.

        Run 'pro help esm-apps' to learn more

        Installed packages with an available esm-apps update:
        (.|\n)+

        Further installed packages covered by esm-apps:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I run `apt upgrade -y` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is attached to an Ubuntu Pro subscription.

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2026\. You have received \d+ security
        update[s]?\.

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2026\. You have received \d+ security
        update[s]?\.
        """
        When I run `pro disable esm-infra esm-apps` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is NOT receiving security patches because the LTS period has ended
        and esm-infra is not enabled.
        This machine is attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026.

        Enable esm-infra with: pro enable esm-infra

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026.

        Enable esm-apps with: pro enable esm-apps
        """
        When I verify root and non-root `pro security-status --thirdparty` calls have the same output
        And I run `pro security-status --thirdparty` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +1 package from a third party

        Packages from third parties are not provided by the official Ubuntu
        archive, for example packages from Personal Package Archives in Launchpad\.

        Packages:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --unavailable` calls have the same output
        And I run `pro security-status --unavailable` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? no longer available for download

        Packages that are not available for download may be left over from a
        previous release of Ubuntu, may have been installed directly from a
        .deb file, or are from a source which has been disabled\.

        Packages:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        This machine is NOT receiving security patches because the LTS period has ended
        and esm-infra is not enabled.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026.

        Run 'pro help esm-infra' to learn more

        Installed packages covered by esm-infra:
        (.|\n)+
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026.

        Run 'pro help esm-apps' to learn more

        Installed packages covered by esm-apps:
        (.|\n)+
        """
        When I verify that running `pro security-status --thirdparty --unavailable` `as non-root` exits `2`
        Then I will see the following on stderr
        """
        usage: security-status [-h] [--format {json,yaml,text}]
                               [--thirdparty | --unavailable | --esm-infra | --esm-apps]
        argument --unavailable: not allowed with argument --thirdparty
        """
        When I run `rm /var/lib/apt/periodic/update-success-stamp` with sudo
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        The system apt cache may be outdated\. Make sure to run
            sudo apt-get update
        to get the latest package information from apt\.

        This machine is NOT receiving security patches because the LTS period has ended
        and esm-infra is not enabled.
        This machine is attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026.

        Enable esm-infra with: pro enable esm-infra

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026.

        Enable esm-apps with: pro enable esm-apps
        """
        When I run `touch -d '-2 days' /var/lib/apt/periodic/update-success-stamp` with sudo
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        The system apt information was updated 2 day\(s\) ago\. Make sure to run
            sudo apt-get update
        to get the latest package information from apt\.

        This machine is NOT receiving security patches because the LTS period has ended
        and esm-infra is not enabled.
        This machine is attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026.

        Enable esm-infra with: pro enable esm-infra

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026.

        Enable esm-apps with: pro enable esm-apps
        """

    @uses.config.contract_token
    Scenario: Run security status in an Ubuntu machine
        Given a `focal` `lxd-container` machine with ubuntu-advantage-tools installed
        When I install third-party / unknown packages in the machine
        # Ansible is in esm-apps
        And I run `apt-get install -y ansible` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is receiving security patching for Ubuntu Main/Restricted
        repository until 2025.
        This machine is NOT attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2030.

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030\. There (is|are) \d+ pending security update[s]?\.

        Try Ubuntu Pro with a free personal subscription on up to 5 machines.
        Learn more at https://ubuntu.com/pro
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository

        This machine is receiving security patching for Ubuntu Main/Restricted
        repository until 2025.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2030.

        Run 'pro help esm-infra' to learn more
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030\. There (is|are) \d+ pending security update[s]?\.

        Run 'pro help esm-apps' to learn more

        Installed packages with an available esm-apps update:
        (.|\n)+

        Further installed packages covered by esm-apps:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I attach `contract_token` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is attached to an Ubuntu Pro subscription.

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2030.

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2030\. There (is|are) \d+ pending security update[s]?\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2030.

        Run 'pro help esm-infra' to learn more
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2030\. There (is|are) \d+ pending security update[s]?\.

        Run 'pro help esm-apps' to learn more

        Installed packages with an available esm-apps update:
        (.|\n)+

        Further installed packages covered by esm-apps:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I run `apt upgrade -y` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is attached to an Ubuntu Pro subscription.

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2030\.

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2030\. You have received \d+ security
        update[s]?\.
        """
        When I run `pro disable esm-infra esm-apps` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        This machine is receiving security patching for Ubuntu Main/Restricted
        repository until 2025.
        This machine is attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2030.

        Enable esm-infra with: pro enable esm-infra

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030.

        Enable esm-apps with: pro enable esm-apps
        """
        When I verify root and non-root `pro security-status --thirdparty` calls have the same output
        And I run `pro security-status --thirdparty` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +1 package from a third party

        Packages from third parties are not provided by the official Ubuntu
        archive, for example packages from Personal Package Archives in Launchpad\.

        Packages:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --unavailable` calls have the same output
        And I run `pro security-status --unavailable` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? no longer available for download

        Packages that are not available for download may be left over from a
        previous release of Ubuntu, may have been installed directly from a
        .deb file, or are from a source which has been disabled\.

        Packages:
        (.|\n)+

        For example, run:
            apt-cache show .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        This machine is receiving security patching for Ubuntu Main/Restricted
        repository until 2025.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2030.

        Run 'pro help esm-infra' to learn more
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030.

        Run 'pro help esm-apps' to learn more

        Installed packages covered by esm-apps:
        (.|\n)+
        """
        When I verify that running `pro security-status --thirdparty --unavailable` `as non-root` exits `2`
        Then I will see the following on stderr
        """
        usage: security-status [-h] [--format {json,yaml,text}]
                               [--thirdparty | --unavailable | --esm-infra | --esm-apps]
        argument --unavailable: not allowed with argument --thirdparty
        """
        When I run `rm /var/lib/apt/periodic/update-success-stamp` with sudo
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        The system apt cache may be outdated\. Make sure to run
            sudo apt-get update
        to get the latest package information from apt\.

        This machine is receiving security patching for Ubuntu Main/Restricted
        repository until 2025.
        This machine is attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2030.

        Enable esm-infra with: pro enable esm-infra

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030.

        Enable esm-apps with: pro enable esm-apps
        """
        When I run `touch -d '-2 days' /var/lib/apt/periodic/update-success-stamp` with sudo
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        The system apt information was updated 2 day\(s\) ago\. Make sure to run
            sudo apt-get update
        to get the latest package information from apt\.

        This machine is receiving security patching for Ubuntu Main/Restricted
        repository until 2025.
        This machine is attached to an Ubuntu Pro subscription.

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2030.

        Enable esm-infra with: pro enable esm-infra

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030.

        Enable esm-apps with: pro enable esm-apps
        """

    # Latest released non-LTS
    Scenario: Run security status in an Ubuntu machine
        Given a `mantic` `lxd-container` machine with ubuntu-advantage-tools installed
        When I install third-party / unknown packages in the machine
        # Ansible is in esm-apps
        And I run `apt-get install -y ansible` with sudo
        And I verify root and non-root `pro security-status` calls have the same output
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        Main/Restricted packages receive updates until 1/2024\.

        Ubuntu Pro is not available for non-LTS releases\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        Main/Restricted packages receive updates until 1/2024\.

        Ubuntu Pro is not available for non-LTS releases\.
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Universe/Multiverse repository

        Ubuntu Pro is not available for non-LTS releases\.
        """
        When I run `rm /var/lib/apt/periodic/update-success-stamp` with sudo
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        The system apt cache may be outdated\. Make sure to run
            sudo apt-get update
        to get the latest package information from apt\.

        Main/Restricted packages receive updates until 1/2024\.

        Ubuntu Pro is not available for non-LTS releases\.
        """
        When I run `touch -d '-2 days' /var/lib/apt/periodic/update-success-stamp` with sudo
        And I run `pro security-status` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository
         +\d+ package[s]? from a third party
         +\d+ package[s]? no longer available for download

        To get more information about the packages, run
            pro security-status --help
        for a list of available options\.

        The system apt information was updated 2 day\(s\) ago\. Make sure to run
            sudo apt-get update
        to get the latest package information from apt\.

        Main/Restricted packages receive updates until 1/2024\.

        Ubuntu Pro is not available for non-LTS releases\.
        """

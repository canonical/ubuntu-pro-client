@uses.config.contract_token
Feature: Security status command behavior

    @series.xenial
    @series.bionic
    @uses.config.machine_type.lxd.container
    Scenario Outline: Run security status with JSON/YAML format
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
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
           | release | package   | service   |
           | xenial  | apport    | esm-infra |
           | bionic  | libkrb5-3 | esm-apps  |

    @series.xenial
    @uses.config.machine_type.lxd.vm
    Scenario: Check for livepatch CVEs in security-status on an Ubuntu machine
        Given a `xenial` machine with ubuntu-advantage-tools installed
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

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario: Run security status in an Ubuntu machine
        Given a `xenial` machine with ubuntu-advantage-tools installed
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
        
        This machine is not attached to an Ubuntu Pro subscription\.
        
        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026 and has \d+ pending security update[s]?\.

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026 and has \d+ pending security update[s]?\.

        Try Ubuntu Pro with a free personal subscription on up to 5 machines.
        Learn more at https://ubuntu.com/pro
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

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2026\. You have received (\d+|no) security
        update[s]?\.

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2026\. You have received (\d+|no) security
        update[s]?\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        Main/Restricted packages are receiving security updates from
        Ubuntu Pro with 'esm-infra' enabled until 2026\. You have received (\d+|no) security
        update[s]?\.

        Run 'pro help esm-infra' to learn more

        Package names in .*bold.* currently have an available update
        with 'esm-infra' enabled
        Packages:
        (.|\n)+

        For example, run:
            apt-cache policy .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2026\. You have received (\d+|no) security
        update[s]?\.

        Run 'pro help esm-apps' to learn more

        Package names in .*bold.* currently have an available update
        with 'esm-apps' enabled
        Packages:
        (.|\n)+

        For example, run:
            apt-cache policy .+
        to learn more about that package\.
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
        
        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026 and has \d+ pending security update[s]?\.
        Enable esm-infra with: pro enable esm-infra

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026 and has \d+ pending security update[s]?\.
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
            apt-cache policy .+
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
            apt-cache policy .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        Ubuntu Pro with 'esm-infra' enabled provides security updates for
        Main/Restricted packages until 2026 and has \d+ pending security update[s]?\.

        Run 'pro help esm-infra' to learn more

        Package names in .*bold.* currently have an available update
        with 'esm-infra' enabled
        Packages:
        (.|\n)+

        For example, run:
            apt-cache policy .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2026 and has 1 pending security update[s]?\.

        Run 'pro help esm-apps' to learn more

        Package names in .*bold.* currently have an available update
        with 'esm-apps' enabled
        Packages:
        (.|\n)+

        For example, run:
            apt-cache policy .+
        to learn more about that package\.
        """
        When I verify that running `pro security-status --thirdparty --unavailable` `as non-root` exits `2`
        Then I will see the following on stderr
        """
        usage: security-status [-h] [--format {json,yaml,text}]
                               [--thirdparty | --unavailable | --esm-infra | --esm-apps]
        argument --unavailable: not allowed with argument --thirdparty
        """

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario: Run security status in an Ubuntu machine
        Given a `focal` machine with ubuntu-advantage-tools installed
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
        
        This machine is not attached to an Ubuntu Pro subscription\.
        
        Main/Restricted packages receive updates with LTS until 2025\.
        
        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030 and has \d+ pending security update[s]?\.

        Try Ubuntu Pro with a free personal subscription on up to 5 machines.
        Learn more at https://ubuntu.com/pro
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

        Main/Restricted packages receive updates with LTS until 2025\.

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2030\. You have received (\d+|no) security
        update[s]?\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        Main/Restricted packages receive updates with LTS until 2025\.

        After the LTS period ends, Main/Restricted packages will get security updates
        from Ubuntu Pro with 'esm-infra' enabled\.
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Universe/Multiverse packages are receiving security updates from
        Ubuntu Pro with 'esm-apps' enabled until 2030\. You have received (\d+|no) security
        update[s]?\.

        Run 'pro help esm-apps' to learn more

        Package names in .*bold.* currently have an available update
        with 'esm-apps' enabled
        Packages:
        (.|\n)+

        For example, run:
            apt-cache policy .+
        to learn more about that package\.
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
        
        Main/Restricted packages receive updates with LTS until 2025\.

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030 and has \d+ pending security update[s]?\.
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
            apt-cache policy .+
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
            apt-cache policy .+
        to learn more about that package\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository

        Main/Restricted packages receive updates with LTS until 2025\.

        After the LTS period ends, Main/Restricted packages will get security updates
        from Ubuntu Pro with 'esm-infra' enabled\.
        """
        When I verify root and non-root `pro security-status --esm-apps` calls have the same output
        And I run `pro security-status --esm-apps` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ package[s]? from Ubuntu Universe/Multiverse repository

        Ubuntu Pro with 'esm-apps' enabled provides security updates for
        Universe/Multiverse packages until 2030 and has 1 pending security update[s]?\.

        Run 'pro help esm-apps' to learn more

        Package names in .*bold.* currently have an available update
        with 'esm-apps' enabled
        Packages:
        (.|\n)+

        For example, run:
            apt-cache policy .+
        to learn more about that package\.
        """
        When I verify that running `pro security-status --thirdparty --unavailable` `as non-root` exits `2`
        Then I will see the following on stderr
        """
        usage: security-status [-h] [--format {json,yaml,text}]
                               [--thirdparty | --unavailable | --esm-infra | --esm-apps]
        argument --unavailable: not allowed with argument --thirdparty
        """

    @series.kinetic
    @uses.config.machine_type.lxd.container
    Scenario: Run security status in an Ubuntu machine
        Given a `kinetic` machine with ubuntu-advantage-tools installed
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

        Main/Restricted packages receive updates until 7/2023\.
        """
        When I verify root and non-root `pro security-status --esm-infra` calls have the same output
        And I run `pro security-status --esm-infra` as non-root
        Then stdout matches regexp:
        """
        \d+ packages installed:
         +\d+ packages from Ubuntu Main/Restricted repository
        
        Main/Restricted packages receive updates until 7/2023\.
        
        Ubuntu Pro is not available for non-LTS releases\.
        """

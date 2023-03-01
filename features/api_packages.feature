Feature: Package related API endpoints

    @series.all
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token
    Scenario Outline: Call packages API endpoints to see information in a Ubuntu machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.packages.summary.v1` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"summary": {"num_esm_apps_packages": \d+, "num_esm_infra_packages": \d+, "num_installed_packages": \d+, "num_main_packages": \d+, "num_multiverse_packages": \d+, "num_restricted_packages": \d+, "num_third_party_packages": \d+, "num_universe_packages": \d+, "num_unknown_packages": \d+}}, "meta": {"environment_vars": \[\]}, "type": "PackageSummary"}, "errors": \[\], "result": "success", "version": ".+", "warnings": \[\]}
        """
        When I run `pro api u.pro.packages.updates.v1` as non-root
        Then stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"summary": {"num_esm_apps_updates": \d+, "num_esm_infra_updates": \d+, "num_standard_security_updates": \d+, "num_standard_updates": \d+, "num_updates": \d+}, "updates": \[.*\]}, "meta": {"environment_vars": \[\]}, "type": "PackageUpdates"}, "errors": \[\], "result": "success", "version": ".+", "warnings": \[\]}
        """
        # Make sure we have an updated system
        When I attach `contract_token` with sudo
        And I run `apt upgrade -y` with sudo
        # Install some outdated package
        And I run `apt install <package>=<outdated_version> -y --allow-downgrades` with sudo
        # See the update there
        When I run `pro api u.pro.packages.updates.v1` as non-root
        Then stdout matches regexp:
        """
        {"download_size": \d+, "origin": ".+", "package": "<package>", "provided_by": "<provided_by>", "status": "upgrade_available", "version": "<candidate_version>"}
        """

        Examples: ubuntu release
            | release | package         | outdated_version | candidate_version        | provided_by       |
            | xenial  | libcurl3-gnutls | 7.47.0-1ubuntu2  | 7.47.0-1ubuntu2.19\+esm7 | esm-infra         |
            | bionic  | libcurl4        | 7.58.0-2ubuntu3  | 7.58.0-2ubuntu3.23       | standard-security |
            | focal   | libcurl4        | 7.68.0-1ubuntu2  | 7.68.0-1ubuntu2.16       | standard-security |
            | jammy   | libcurl4        | 7.81.0-1         | 7.81.0-1ubuntu1.8        | standard-security |
            | kinetic | libcurl4        | 7.85.0-1         | 7.85.0-1ubuntu0.3        | standard-security |

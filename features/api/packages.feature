Feature: Package related API endpoints

  @uses.config.contract_token
  Scenario Outline: Call packages API endpoints to see information in a Ubuntu machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro api u.pro.packages.summary.v1` as non-root
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "summary": {
            "num_esm_apps_packages": \d+,
            "num_esm_infra_packages": \d+,
            "num_installed_packages": \d+,
            "num_main_packages": \d+,
            "num_multiverse_packages": \d+,
            "num_restricted_packages": \d+,
            "num_third_party_packages": \d+,
            "num_universe_packages": \d+,
            "num_unknown_packages": \d+
          }
        },
        "meta": {
          "environment_vars": []
        },
        "type": "PackageSummary"
      }
      """
    When I run `pro api u.pro.packages.updates.v1` as non-root
    Then stdout matches regexp:
      """
      {"_schema_version": "v1", "data": {"attributes": {"summary": {"num_esm_apps_updates": \d+, "num_esm_infra_updates": \d+, "num_standard_security_updates": \d+, "num_standard_updates": \d+, "num_updates": \d+}, "updates": \[.*\]}, "meta": {"environment_vars": \[\]}, "type": "PackageUpdates"}, "errors": \[\], "result": "success", "version": ".+", "warnings": \[\]}
      """
    # Make sure we have an updated system
    When I attach `contract_token` with sudo
    And I apt upgrade
    # Install some outdated package
    And I apt install `<package>=<outdated_version>`
    # See the update there
    When I store candidate version of package `<package>`
    And I regexify `candidate` stored var
    And I run `pro api u.pro.packages.updates.v1` as non-root
    Then stdout matches regexp:
      """
      {"download_size": \d+, "origin": ".+", "package": "<package>", "provided_by": "<provided_by>", "status": "upgrade_available", "version": "$behave_var{stored_var candidate}"}
      """

    Examples: ubuntu release
      | release | machine_type  | package         | outdated_version | provided_by       |
      | xenial  | lxd-container | libcurl3-gnutls | 7.47.0-1ubuntu2  | esm-infra         |
      | bionic  | lxd-container | libcurl4        | 7.58.0-2ubuntu3  | esm-infra         |
      | bionic  | wsl           | libcurl4        | 7.58.0-2ubuntu3  | esm-infra         |
      | focal   | lxd-container | libcurl4        | 7.68.0-1ubuntu2  | standard-security |
      | focal   | wsl           | libcurl4        | 7.68.0-1ubuntu2  | standard-security |
      | jammy   | lxd-container | libcurl4        | 7.81.0-1         | standard-security |
      | jammy   | wsl           | libcurl4        | 7.81.0-1         | standard-security |
      | mantic  | lxd-container | libcurl4        | 8.2.1-1ubuntu3   | standard-security |

Feature: Command behaviour when trying to attach a machine to an Ubuntu
         Advantage subscription using an invalid token

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attach command failure on invalid token
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `ua attach INVALID_TOKEN` `with sudo` exits `1`
        Then stderr matches regexp:
            """
            Invalid token. See https://ubuntu.com/advantage
            """
        When I verify that running `ua attach INVALID_TOKEN` `as non-root` exits `1`
        Then I will see the following on stderr:
             """
             This command must be run as root (try using sudo).
             """
        When I verify that running `ua attach invalid-token --format json` `with sudo` exits `1`
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "Invalid token. See https://ubuntu.com/advantage", "message_code": "attach-invalid-token", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | impish  |
           | jammy   |

    @series.all
    @uses.config.machine_type.lxd.container
    @uses.config.contract_token_staging_expired
    Scenario Outline: Attach command failure on expired token
       Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attempt to attach `contract_token_staging_expired` with sudo
        Then stderr matches regexp:
             """
             Attach denied:
             Contract ".*" .*
             Visit https://ubuntu.com/advantage to manage contract tokens.
             """
        When I verify that running attach `with sudo` using expired token with json response fails
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"additional_info": {"contract_expiry_date": "12-31-2019", "contract_id": "cAJ4NHcl2qAld2CbJt5cufzZNHgVZ0YTPIH96Ihsy4bU"}, "message": "Attach denied:\nContract \"cAJ4NHcl2qAld2CbJt5cufzZNHgVZ0YTPIH96Ihsy4bU\" expired on December 31, 2019\nVisit https://ubuntu.com/advantage to manage contract tokens.", "message_code": "attach-forbidden-expired", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | impish  |
           | jammy   |

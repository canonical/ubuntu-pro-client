Feature: Command behaviour when trying to attach a machine to an Ubuntu
         Pro subscription using an invalid token

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attach command failure on invalid token
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `pro attach INVALID_TOKEN` `with sudo` exits `1`
        Then stderr matches regexp:
            """
            Invalid token. See https://ubuntu.com/pro
            """
        When I verify that running `pro attach INVALID_TOKEN` `as non-root` exits `1`
        Then I will see the following on stderr:
             """
             This command must be run as root (try using sudo).
             """
        When I verify that running `pro attach invalid-token --format json` `with sudo` exits `1`
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"message": "Invalid token. See https://ubuntu.com/pro", "message_code": "attach-invalid-token", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
           | kinetic |

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
             Visit https://ubuntu.com/pro to manage contract tokens.
             """
        When I verify that running attach `with sudo` using expired token with json response fails
        Then stdout is a json matching the `ua_operation` schema
        And I will see the following on stdout:
            """
            {"_schema_version": "0.1", "errors": [{"additional_info": {"contract_expiry_date": "08-21-2022", "contract_id": "cAHT7ADjWMRCjo5Q53QlTawtPlrhxeRg7cbEnquxxm1g"}, "message": "Attach denied:\nContract \"cAHT7ADjWMRCjo5Q53QlTawtPlrhxeRg7cbEnquxxm1g\" expired on August 21, 2022\nVisit https://ubuntu.com/pro to manage contract tokens.", "message_code": "attach-forbidden-expired", "service": null, "type": "system"}], "failed_services": [], "needs_reboot": false, "processed_services": [], "result": "failure", "warnings": []}
            """

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
           | kinetic |

Feature: Magic attach flow related tests

    @series.lts
    @uses.config.machine_type.lxd-container
    Scenario Outline: Attach using the magic attach flow
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I change contract to staging with sudo
        And I create the file `/tmp/response-overlay.json` with the following:
        """
        {
            "https://contracts.staging.canonical.com/v1/magic-attach": [
            {
              "code": 200,
              "response": {
                "userCode": "123",
                "token": "testToken",
                "expires": "expire-date",
                "expiresIn": 2000
              }
            },
            {
                "code": 200,
                "response": {
                    "userCode": "123",
                    "token": "testToken",
                    "expires": "expire-date",
                    "expiresIn": 2000,
                    "contractID": "test-contract-id",
                    "contractToken": "$behave_var{contract_token_staging}"
                }
            }]
        }
        """
        And I append the following on uaclient config:
        """
        features:
          serviceclient_url_responses: "/tmp/response-overlay.json"
        """
        And I run `pro attach` with sudo
        Then stdout matches regexp:
        """
        Initiating attach operation...

        Please sign in to your Ubuntu Pro account at this link:
        https://ubuntu.com/pro/attach
        And provide the following code: .*123.*

        Attaching the machine...
        """
        And the machine is attached

        Examples: ubuntu release
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |

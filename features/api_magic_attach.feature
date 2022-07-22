Feature: Magic Attach endpoints

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Call magic attach endpoints
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `pro api u.pro.attach.magic.revoke.v1` `as non-root` exits `1`
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"meta": {\"environment_vars\": \[]}}, "errors": \[{"code": "api-missing-argument", "meta": {}, "title": "Missing argument \'magic_token\' for endpoint u.pro.attach.magic.revoke.v1"}\], "result": "failure", "version": ".*", "warnings": \[\]}
        """
        When I initiate the magic attach flow
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `magic_attach` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"expires": ".*", "expires_in": .*, "token": ".*", "user_code": ".*"}, "meta": {\"environment_vars\": \[]}, "type": "MagicAttachInitiate"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I create the file `/tmp/response-overlay.json` with the following:
        """
        {
            "https://contracts.canonical.com/v1/magic-attach": [
            {
              "code": 200,
              "response": {
                "userCode": "123",
                "token": "testToken",
                "expires": "expire-date",
                "expiresIn": 2000,
                "contractID": "test-contract-id",
                "contractToken": "contract-token"
              }
            }]
        }
        """
        And I append the following on uaclient config:
        """
        features:
          serviceclient_url_responses: "/tmp/response-overlay.json"
        """
        And I wait for the magic attach token to be activated
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `magic_attach` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"contract_id": "test-contract-id", "contract_token": "contract-token", "expires": "expire-date", "expires_in": 2000, "token": "testToken", "user_code": "123"}, "meta": {\"environment_vars\": \[]}, "type": "MagicAttachWait"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I revoke the magic attach token
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {}, "meta": {\"environment_vars\": \[]}, "type": "MagicAttachRevoke"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |

Feature: Magic Attach endpoints

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Call magic attach endpoints
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I verify that running `pro api u.pro.attach.magic.initiate.v1` `as non-root` exits `1`
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {}, "errors": \[{"code": "api-error", "meta": {}, "title": "Missing argument 'email' for endpoint u.pro.attach.magic.initiate.v1"}\], "result": "failure", "version": ".*", "warnings": \[\]}
        """
        When I verify that running `pro api u.pro.attach.magic.initiate.v1 --args email=invalid-email` `as non-root` exits `1`
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {}, "errors": \[{"code": "magic-attach-invalid-email", "meta": {}, "title": "invalid-email is not a valid email."}\], "result": "failure", "version": .*", "warnings": \[\]}
        """
        When I initiate the magic attach flow using the API for email `test@test.com`
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `magic_attach` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {"_schema": "0.1", "confirmation_code": ".*", "expires": ".*", "token": ".*", "user_email": "test@test.com"}, "meta": {}, "type": "MagicAttachInitiate"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I create the file `/tmp/response-overlay.json` with the following:
        """
        {
            "https://contracts.canonical.com/v1/magic-attach": [
            {
              "code": 200,
              "response": {
                "confirmationCode": "123",
                "token": "testToken",
                "expires": "expire-date",
                "userEmail": "test@test.com",
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
        {"_schema_version": "v1", "data": {"attributes": {"_schema": "0.1", "confirmation_code": "123", "contract_id": "test-contract-id", "contract_token": "contract-token", "expires": "expire-date", "token": "testToken", "user_email": "test@test.com"}, "meta": {}, "type": "MagicAttachWait"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        And I revoke the magic attach token
        Then stdout is a json matching the `api_response` schema
        And stdout matches regexp:
        """
        {"_schema_version": "v1", "data": {"attributes": {}, "meta": {}, "type": "MagicAttachRevoke"}, "errors": \[\], "result": "success", "version": ".*", "warnings": \[\]}
        """

        Examples: ubuntu release
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |

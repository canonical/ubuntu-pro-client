Feature: api.u.pro.token_info.v1

  @uses.config.contract_token
  Scenario Outline: Get token info from api
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify root and non-root `pro api u.pro.token_info.v1 --args token=$behave_var{contract_token}` calls have the same output
    When I run `pro api u.pro.token_info.v1 --args token=$behave_var{contract_token}` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `api_token_info_response` schema
    When I apply this jq filter `.attributes.services[] | {name: .name, available: .available}` to the API data field output
    Then if `<release>` in `xenial or bionic` then output is:
      """
      {"name": "anbox-cloud", "available": false}
      {"name": "cc-eal", "available": true}
      {"name": "cis", "available": true}
      {"name": "esm-apps", "available": true}
      {"name": "esm-infra", "available": true}
      {"name": "fips", "available": true}
      {"name": "fips-preview", "available": false}
      {"name": "fips-updates", "available": true}
      {"name": "landscape", "available": false}
      {"name": "livepatch", "available": true}
      {"name": "realtime-kernel", "available": false}
      {"name": "ros", "available": true}
      {"name": "ros-updates", "available": true}
      """
    And if `<release>` in `focal` then output is:
      """
      {"name": "anbox-cloud", "available": true}
      {"name": "cc-eal", "available": false}
      {"name": "esm-apps", "available": true}
      {"name": "esm-infra", "available": true}
      {"name": "fips", "available": true}
      {"name": "fips-preview", "available": false}
      {"name": "fips-updates", "available": true}
      {"name": "landscape", "available": false}
      {"name": "livepatch", "available": true}
      {"name": "realtime-kernel", "available": false}
      {"name": "ros", "available": true}
      {"name": "ros-updates", "available": false}
      {"name": "usg", "available": true}
      """
    And if `<release>` in `jammy` then output is:
      """
      {"name": "anbox-cloud", "available": true}
      {"name": "cc-eal", "available": false}
      {"name": "esm-apps", "available": true}
      {"name": "esm-infra", "available": true}
      {"name": "fips", "available": false}
      {"name": "fips-preview", "available": true}
      {"name": "fips-updates", "available": true}
      {"name": "landscape", "available": false}
      {"name": "livepatch", "available": true}
      {"name": "realtime-kernel", "available": true}
      {"name": "ros", "available": false}
      {"name": "ros-updates", "available": false}
      {"name": "usg", "available": true}
      """
    And if `<release>` in `noble` then output is:
      """
      {"name": "anbox-cloud", "available": true}
      {"name": "cc-eal", "available": false}
      {"name": "esm-apps", "available": true}
      {"name": "esm-infra", "available": true}
      {"name": "fips", "available": false}
      {"name": "fips-preview", "available": false}
      {"name": "fips-updates", "available": false}
      {"name": "landscape", "available": true}
      {"name": "livepatch", "available": true}
      {"name": "realtime-kernel", "available": true}
      {"name": "ros", "available": false}
      {"name": "ros-updates", "available": false}
      {"name": "usg", "available": false}
      """
    And if `release` in `oracular` then output is:
      """
      {"name": "anbox-cloud", "available": true}
      {"name": "cc-eal", "available": false}
      {"name": "esm-apps", "available": true}
      {"name": "esm-infra", "available": true}
      {"name": "fips", "available": true}
      {"name": "fips-preview", "available": false}
      {"name": "fips-updates", "available": true}
      {"name": "landscape", "available": false}
      {"name": "livepatch", "available": true}
      {"name": "realtime-kernel", "available": false}
      {"name": "ros", "available": true}
      {"name": "ros-updates", "available": false}
      {"name": "usg", "available": true}
      """
    When I verify that running `pro api u.pro.token_info.v1` `with sudo` exits `1`
    Then API errors field output matches regexp:
      """
      [
        {
          "code": "api-missing-argument",
          "meta": {
            "arg": "token",
            "endpoint": "u.pro.token_info.v1"
          },
          "title": "Missing argument 'token' for endpoint u.pro.token_info.v1"
        }
      ]
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |

  @uses.config.contract_token_staging_expired
  Scenario Outline: Check api with an expired contract token
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I change contract to staging with sudo
    Then I verify that running `pro api u.pro.token_info.v1 --args token=$behave_var{contract_token_staging_expired}` `as non-root` exits `1`
    Then API errors field output matches regexp:
      """
      [
        {
          "code": "token-forbidden-expired",
          "meta": {
            "contract_expiry_date": "08-21-2022",
            "contract_id": ".*",
            "date": "August 21, 2022"
          },
          "title": "Contract .* expired on .*"
        }
      ]
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |

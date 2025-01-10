Feature: Services list api

  @uses.config.contract_token
  Scenario Outline: Get services list when unattached/attached as non-root
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify root and non-root `pro api u.pro.services.list.v1` calls have the same output
    When I run `pro api u.pro.services.list.v1` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `api_service_list_response` schema
    When I apply this jq filter `.attributes.services[] | {name: .name, available: .available, entitled: .entitled}` to the API data field output
    Then if `<release>` in `xenial or bionic` then output is:
      """
      {"name": "anbox-cloud", "available": false, "entitled": null}
      {"name": "cc-eal", "available": true, "entitled": null}
      {"name": "cis", "available": true, "entitled": null}
      {"name": "esm-apps", "available": true, "entitled": null}
      {"name": "esm-infra", "available": true, "entitled": null}
      {"name": "fips", "available": true, "entitled": null}
      {"name": "fips-preview", "available": false, "entitled": null}
      {"name": "fips-updates", "available": true, "entitled": null}
      {"name": "landscape", "available": false, "entitled": null}
      {"name": "livepatch", "available": true, "entitled": null}
      {"name": "realtime-kernel", "available": false, "entitled": null}
      {"name": "ros", "available": true, "entitled": null}
      {"name": "ros-updates", "available": true, "entitled": null}
      """
    And if `<release>` in `focal` then output is:
      """
      {"name": "anbox-cloud", "available": true, "entitled": null}
      {"name": "cc-eal", "available": false, "entitled": null}
      {"name": "esm-apps", "available": true, "entitled": null}
      {"name": "esm-infra", "available": true, "entitled": null}
      {"name": "fips", "available": true, "entitled": null}
      {"name": "fips-preview", "available": false, "entitled": null}
      {"name": "fips-updates", "available": true, "entitled": null}
      {"name": "landscape", "available": false, "entitled": null}
      {"name": "livepatch", "available": true, "entitled": null}
      {"name": "realtime-kernel", "available": false, "entitled": null}
      {"name": "ros", "available": true, "entitled": null}
      {"name": "ros-updates", "available": false, "entitled": null}
      {"name": "usg", "available": true, "entitled": null}
      """
    And if `<release>` in `jammy` then output is:
      """
      {"name": "anbox-cloud", "available": true, "entitled": null}
      {"name": "cc-eal", "available": false, "entitled": null}
      {"name": "esm-apps", "available": true, "entitled": null}
      {"name": "esm-infra", "available": true, "entitled": null}
      {"name": "fips", "available": false, "entitled": null}
      {"name": "fips-preview", "available": true, "entitled": null}
      {"name": "fips-updates", "available": true, "entitled": null}
      {"name": "landscape", "available": false, "entitled": null}
      {"name": "livepatch", "available": true, "entitled": null}
      {"name": "realtime-kernel", "available": true, "entitled": null}
      {"name": "ros", "available": false, "entitled": null}
      {"name": "ros-updates", "available": false, "entitled": null}
      {"name": "usg", "available": true, "entitled": null}
      """
    And if `<release>` in `noble` then output is:
      """
      {"name": "anbox-cloud", "available": true, "entitled": null}
      {"name": "cc-eal", "available": false, "entitled": null}
      {"name": "esm-apps", "available": true, "entitled": null}
      {"name": "esm-infra", "available": true, "entitled": null}
      {"name": "fips", "available": false, "entitled": null}
      {"name": "fips-preview", "available": false, "entitled": null}
      {"name": "fips-updates", "available": false, "entitled": null}
      {"name": "landscape", "available": true, "entitled": null}
      {"name": "livepatch", "available": true, "entitled": null}
      {"name": "realtime-kernel", "available": true, "entitled": null}
      {"name": "ros", "available": false, "entitled": null}
      {"name": "ros-updates", "available": false, "entitled": null}
      {"name": "usg", "available": false, "entitled": null}
      """
    And if `<release>` in `oracular` then output is:
      """
      {"name": "anbox-cloud", "available": false, "entitled": null}
      {"name": "cc-eal", "available": false, "entitled": null}
      {"name": "cis", "available": false, "entitled": null}
      {"name": "esm-apps", "available": false, "entitled": null}
      {"name": "esm-infra", "available": false, "entitled": null}
      {"name": "fips", "available": false, "entitled": null}
      {"name": "fips-preview", "available": false, "entitled": null}
      {"name": "fips-updates", "available": false, "entitled": null}
      {"name": "landscape", "available": false, "entitled": null}
      {"name": "livepatch", "available": false, "entitled": null}
      {"name": "realtime-kernel", "available": false, "entitled": null}
      {"name": "ros", "available": false, "entitled": null}
      {"name": "ros-updates", "available": false, "entitled": null}
      """
    When I attach `contract_token` with sudo
    When I verify root and non-root `pro api u.pro.services.list.v1` calls have the same output
    When I run `pro api u.pro.services.list.v1` as non-root
    Then stdout is a json matching the `api_response` schema
    And the json API response data matches the `api_service_list_response` schema
    When I apply this jq filter `.attributes.services[] | {name: .name, available: .available, entitled: .entitled}` to the API data field output
    Then if `<release>` in `xenial or bionic` then output is:
      """
      {"name": "anbox-cloud", "available": false, "entitled": true}
      {"name": "cc-eal", "available": true, "entitled": true}
      {"name": "cis", "available": true, "entitled": true}
      {"name": "esm-apps", "available": true, "entitled": true}
      {"name": "esm-infra", "available": true, "entitled": true}
      {"name": "fips", "available": true, "entitled": true}
      {"name": "fips-preview", "available": false, "entitled": true}
      {"name": "fips-updates", "available": true, "entitled": true}
      {"name": "landscape", "available": false, "entitled": true}
      {"name": "livepatch", "available": false, "entitled": true}
      {"name": "realtime-kernel", "available": false, "entitled": true}
      {"name": "ros", "available": true, "entitled": true}
      {"name": "ros-updates", "available": true, "entitled": true}
      """
    And if `<release>` in `focal` then output is:
      """
      {"name": "anbox-cloud", "available": true, "entitled": true}
      {"name": "cc-eal", "available": false, "entitled": true}
      {"name": "esm-apps", "available": true, "entitled": true}
      {"name": "esm-infra", "available": true, "entitled": true}
      {"name": "fips", "available": true, "entitled": true}
      {"name": "fips-preview", "available": false, "entitled": true}
      {"name": "fips-updates", "available": true, "entitled": true}
      {"name": "landscape", "available": false, "entitled": true}
      {"name": "livepatch", "available": false, "entitled": true}
      {"name": "realtime-kernel", "available": false, "entitled": true}
      {"name": "ros", "available": true, "entitled": true}
      {"name": "ros-updates", "available": false, "entitled": true}
      {"name": "usg", "available": true, "entitled": true}
      """
    And if `<release>` in `jammy` then output is:
      """
      {"name": "anbox-cloud", "available": true, "entitled": true}
      {"name": "cc-eal", "available": false, "entitled": true}
      {"name": "esm-apps", "available": true, "entitled": true}
      {"name": "esm-infra", "available": true, "entitled": true}
      {"name": "fips", "available": false, "entitled": true}
      {"name": "fips-preview", "available": true, "entitled": true}
      {"name": "fips-updates", "available": true, "entitled": true}
      {"name": "landscape", "available": false, "entitled": true}
      {"name": "livepatch", "available": false, "entitled": true}
      {"name": "realtime-kernel", "available": false, "entitled": true}
      {"name": "ros", "available": false, "entitled": true}
      {"name": "ros-updates", "available": false, "entitled": true}
      {"name": "usg", "available": true, "entitled": true}
      """
    And if `<release>` in `noble` then output is:
      """
      {"name": "anbox-cloud", "available": true, "entitled": true}
      {"name": "cc-eal", "available": false, "entitled": true}
      {"name": "esm-apps", "available": true, "entitled": true}
      {"name": "esm-infra", "available": true, "entitled": true}
      {"name": "fips", "available": false, "entitled": true}
      {"name": "fips-preview", "available": false, "entitled": true}
      {"name": "fips-updates", "available": false, "entitled": true}
      {"name": "landscape", "available": true, "entitled": true}
      {"name": "livepatch", "available": false, "entitled": true}
      {"name": "realtime-kernel", "available": false, "entitled": true}
      {"name": "ros", "available": false, "entitled": true}
      {"name": "ros-updates", "available": false, "entitled": true}
      {"name": "usg", "available": false, "entitled": true}
      """
    And if `<release>` in `oracular` then output is:
      """
      {"name": "anbox-cloud", "available": false, "entitled": true}
      {"name": "cc-eal", "available": false, "entitled": true}
      {"name": "cis", "available": false, "entitled": true}
      {"name": "esm-apps", "available": false, "entitled": true}
      {"name": "esm-infra", "available": false, "entitled": true}
      {"name": "fips", "available": false, "entitled": true}
      {"name": "fips-preview", "available": false, "entitled": true}
      {"name": "fips-updates", "available": false, "entitled": true}
      {"name": "landscape", "available": false, "entitled": true}
      {"name": "livepatch", "available": false, "entitled": true}
      {"name": "realtime-kernel", "available": false, "entitled": true}
      {"name": "ros", "available": false, "entitled": true}
      {"name": "ros-updates", "available": false, "entitled": true}
      """

    Examples: ubuntu release
      | release  | machine_type  |
      | xenial   | lxd-container |
      | bionic   | lxd-container |
      | focal    | lxd-container |
      | jammy    | lxd-container |
      | noble    | lxd-container |
      | oracular | lxd-container |

Feature: u.pro.attach.guest.get_guest_token.v1

  Scenario Outline: u.pro.attach.guest.get_guest_token.v1
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I verify that running `pro api u.pro.attach.guest.get_guest_token.v1` `as non-root` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "nonroot-user",
          "meta": {},
          "title": "This command must be run as root (try using sudo)."
        }
      ]
      """
    When I verify that running `pro api u.pro.attach.guest.get_guest_token.v1` `with sudo` exits `1`
    Then API errors field output is:
      """
      [
        {
          "code": "unattached",
          "meta": {},
          "title": "This machine is not attached to an Ubuntu Pro subscription.\nSee https://ubuntu.com/pro"
        }
      ]
      """
    When I attach `contract_token` with sudo and options `--no-auto-enable`
    When I run `pro api u.pro.attach.guest.get_guest_token.v1` with sudo
    Then API data field output matches regexp:
      """
      {
        "attributes": {
          "expires": ".*",
          "guest_token": ".*",
          "id": ".*"
        },
        "meta": {
          "environment_vars": []
        },
        "type": "GetGuestToken"
      }
      """

    Examples:
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

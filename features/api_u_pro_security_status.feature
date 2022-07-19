Feature: api.u.pro.security.status

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: v1
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.status.v1` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `api_u_pro_security_status_v1` schema
        When I create the file `/tmp/script.py` with the following:
        """
        from uaclient.api.u.pro.security.status.v1 import status

        res = status()

        assert(res.summary.ua.attached == False)
        print(res.to_json())
        """
        When I run `python3 /tmp/script.py` with sudo
        Then stdout is a json matching the `api_u_pro_security_status_v1` schema

        Examples: ubuntu release
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: b2
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `pro api u.pro.security.status.v2` with sudo
        Then stdout is a json matching the `api_response` schema
        And the json API response data matches the `api_u_pro_security_status_v2` schema
        When I create the file `/tmp/script.py` with the following:
        """
        from uaclient.api.u.pro.security.status.v2 import status

        res = status()

        assert(res.summary.pro.attached == False)
        print(res.to_json())
        """
        When I run `python3 /tmp/script.py` with sudo
        Then stdout is a json matching the `api_u_pro_security_status_v2` schema

        Examples: ubuntu release
            | release |
            | xenial  |
            | bionic  |
            | focal   |
            | jammy   |

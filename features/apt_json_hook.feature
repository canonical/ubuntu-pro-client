Feature: APT JSON Hook

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT JSON Hook prints package counts correctly on xenial
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `apt-get update` with sudo
        When I run `apt-get upgrade -y` with sudo

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard security updates

        """

        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates

        """

        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 esm-apps security update

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        4 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard security updates and 2 esm-infra updates

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard security updates and 1 esm-apps update

        """

        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates and 1 esm-apps update

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        5 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard security updates, 2 esm-infra updates and 1 esm-apps update

        """

        When I run `apt-get upgrade -y` with sudo
        Then stdout matches regexp:
        """
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        Then stdout does not match regexp:
        """
        standard security update
        """
        Then stdout does not match regexp:
        """
        esm-infra
        """
        Then stdout does not match regexp:
        """
        esm-apps
        """

        Examples: ubuntu release
           | release | standard-pkg                                                          | infra-pkg                                            | apps-pkg |
           | xenial  | accountsservice=0.6.40-2ubuntu10 libaccountsservice0=0.6.40-2ubuntu10 | curl=7.47.0-1ubuntu2 libcurl3-gnutls=7.47.0-1ubuntu2 | libzstd1=1.3.1+dfsg-1~ubuntu0.16.04.1 |

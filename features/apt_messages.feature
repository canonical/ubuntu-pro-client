Feature: APT Messages

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT JSON Hook prints package counts correctly on xenial
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        When I run `apt-get update` with sudo
        When I run `apt-get upgrade -y` with sudo

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates

        """

        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        2 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates

        """

        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        1 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        1 esm-apps security update

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        4 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates and 2 esm-infra security updates

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates and 1 esm-apps security update

        """

        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 esm-infra security updates and 1 esm-apps security update

        """

        When I run `apt-get install -y --allow-downgrades <standard-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <infra-pkg>` with sudo
        When I run `apt-get install -y --allow-downgrades <apps-pkg>` with sudo
        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        5 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        2 standard LTS security updates, 2 esm-infra security updates and 1 esm-apps security update

        """

        When I run `apt upgrade -y` with sudo
        Then stdout matches regexp:
        """
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        Then stdout does not match regexp:
        """
        standard LTS security update
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
           | release | standard-pkg                                                          | infra-pkg                                            | apps-pkg     |
           | xenial  | accountsservice=0.6.40-2ubuntu10 libaccountsservice0=0.6.40-2ubuntu10 | curl=7.47.0-1ubuntu2 libcurl3-gnutls=7.47.0-1ubuntu2 | hello=2.10-1 |

    @series.xenial
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT Hook advertises esm-infra on upgrade
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `apt-get -y upgrade` with sudo
        When I run `apt-get -y autoremove` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #
        The following security updates require Ubuntu Pro with 'esm-infra' enabled:
          .*
        Learn more about Ubuntu Pro for 16\.04 at https:\/\/ubuntu\.com\/16-04
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        When I attach `contract_token` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #
        The following packages will be upgraded:
        """
        When I update contract to use `effectiveTo` as `days=+2`
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #

        CAUTION: Your Ubuntu Pro subscription will expire in 2 days.
        Renew your subscription at https:\/\/ubuntu.com\/pro to ensure continued security
        coverage for your applications.

        The following packages will be upgraded:
        """
        When I update contract to use `effectiveTo` as `days=-3`
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #

        CAUTION: Your Ubuntu Pro subscription expired on \d+ \w+ \d+.
        Renew your subscription at https:\/\/ubuntu.com\/pro to ensure continued security
        coverage for your applications.
        Your grace period will expire in 11 days.

        The following packages will be upgraded:
        """
        When I update contract to use `effectiveTo` as `days=-20`
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #

        \*Your Ubuntu Pro subscription has EXPIRED\*
        The following security updates require Ubuntu Pro with 'esm-infra' enabled:
          .*
        Renew your service at https:\/\/ubuntu.com\/pro

        The following packages will be upgraded:
        """
        When I run `apt-get upgrade -y` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #

        \*Your Ubuntu Pro subscription has EXPIRED\*
        Renew your service at https:\/\/ubuntu.com\/pro

        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        When I run `pro detach --assume-yes` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #
        Receive additional future security updates with Ubuntu Pro.
        Learn more about Ubuntu Pro for 16\.04 at https:\/\/ubuntu\.com\/16-04
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        Examples: ubuntu release
          | release |
          | xenial  |

    @series.focal
    @uses.config.machine_type.lxd.container
    Scenario Outline: APT Hook advertises esm-apps on upgrade
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `apt-get -y upgrade` with sudo
        When I run `apt-get -y autoremove` with sudo
        When I run `apt-get install hello` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then I will see the following on stdout:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;)
        # Use 'pro config set apt_news=false' to hide this and future APT news.
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
        """
        When I run `apt-get upgrade` with sudo
        Then stdout does not match regexp:
        """
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #
        """
        When I attach `contract_token` with sudo
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #
        The following packages will be upgraded:
          hello
        """
#        When I update contract to use `effectiveTo` as `days=-20`
#        When I run `pro refresh messages` with sudo
#        When I run `apt upgrade --dry-run` with sudo
#        Then stdout matches regexp:
#        """
#        Reading package lists...
#        Building dependency tree...
#        Reading state information...
#        Calculating upgrade...
#
#        \*Your Ubuntu Pro subscription has EXPIRED\*
#        The following security updates require Ubuntu Pro with 'esm-apps' enabled:
#          hello
#        Renew your service at https:\/\/ubuntu.com\/pro
#
#        The following packages will be upgraded:
#        """
        When I run `apt-get upgrade -y` with sudo
        When I run `pro detach --assume-yes` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt upgrade` with sudo
        Then stdout matches regexp:
        """
        Reading package lists...
        Building dependency tree...
        Reading state information...
        Calculating upgrade...
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #
        0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded\.
        """
        When I run `pro config set apt_news=false` with sudo
        And I run `apt upgrade` with sudo
        Then stdout does not match regexp:
        """
        #
        # News about significant security updates, features and services will
        # appear here to raise awareness and perhaps tease /r/Linux ;\)
        # Use 'pro config set apt_news=false' to hide this and future APT news\.
        #
        """
        Examples: ubuntu release
          | release |
          | focal   |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.aws.generic
    Scenario Outline: AWS URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt-get upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        <msg>
        """
        Examples: ubuntu release
          | release | msg                                                                    |
          | xenial  | Learn more about Ubuntu Pro for 16\.04 at https:\/\/ubuntu\.com\/16-04 |
#          | bionic  | Learn more about Ubuntu Pro on AWS at https:\/\/ubuntu\.com\/aws\/pro  |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.azure.generic
    Scenario Outline: Azure URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt-get upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        <msg>
        """
        Examples: ubuntu release
          | release | msg                                                                                    |
          | xenial  | Learn more about Ubuntu Pro for 16\.04 on Azure at https:\/\/ubuntu\.com\/16-04\/azure |
#          | bionic  | Learn more about Ubuntu Pro on Azure at https:\/\/ubuntu\.com\/azure\/pro              |

    @series.xenial
    @series.bionic
    @uses.config.machine_type.gcp.generic
    Scenario Outline: GCP URLs
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I run `apt-get update` with sudo
        When I run `pro refresh messages` with sudo
        When I run `apt-get upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        <msg>
        """
        Examples: ubuntu release
          | release | msg                                                                    |
          | xenial  | Learn more about Ubuntu Pro for 16\.04 at https:\/\/ubuntu\.com\/16-04 |
#          | bionic  | Learn more about Ubuntu Pro on GCP at https:\/\/ubuntu\.com\/gcp\/pro  |

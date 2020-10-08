Feature: Upgrade between releases when uaclient is attached

   @series.focal
   @upgrade
   Scenario Outline: Attached upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt-get dist-upgrade --assume-yes` with sudo
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        And I run `sed -i 's/Prompt=lts/Prompt=normal/' /etc/update-manager/release-upgrades` with sudo
        Then I verify that running `do-release-upgrade --devel-release --frontend=DistUpgradeViewNonInteractive` `with sudo` exits `0`
        When I reboot the `<release>` machine
        And I run `lsb_release -cs` as non-root
        Then I will see the following on stdout:
        """
        <next_release>
        """
        When I run `egrep "<release>|disabled" /etc/apt/sources.list.d/*` as non-root
        Then I will see the following on stdout:
        """
        """
        When I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra     yes                n/a
        """
   
        Examples: ubuntu release
        | release | next_release | devel_release   |
        | focal  | groovy        | --devel-release |

   @series.bionic
   @upgrade
   Scenario Outline: Attached upgrade across LTS releases
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `apt-get dist-upgrade --assume-yes` with sudo
        And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
        """
        [Sources]
        AllowThirdParty=yes
        """
        And I run `wget http://archive.ubuntu.com/ubuntu/dists/<next_release>-updates/main/dist-upgrader-all/current/<next_release>.tar.gz -P /tmp/` with sudo
        And I run `tar zxvf /tmp/<next_release>.tar.gz -C /tmp/` with sudo
        And I run `wget https://git.launchpad.net/~chad.smith/ubuntu-release-upgrader/plain/DistUpgrade/DistUpgradeController.py?h=esm-support-pro-upgrades -O /tmp/DistUpgradeController.py` with sudo
        And I run `wget https://git.launchpad.net/~chad.smith/ubuntu-release-upgrader/plain/data/mirrors.cfg?h=esm-support-pro-upgrades -O /tmp/mirrors.cfg` with sudo
        And I run `apt-get remove ubuntu-release-upgrader-core -y` with sudo
        And I run `apt remove python3-distupgrade -y` with sudo
        Then I verify that running `/tmp/<next_release> <devel_release> --datadir=/tmp --frontend=DistUpgradeViewNonInteractive` `with sudo` exits `0`
        When I reboot the `<release>` machine
        And I run `lsb_release -cs` as non-root
        Then I will see the following on stdout:
        """
        <next_release>
        """
        When I run `egrep "<release>|disabled" /etc/apt/sources.list.d/*` as non-root
        Then I will see the following on stdout:
        """
        """
        When I run `ua status` with sudo
        Then stdout matches regexp:
        """
        esm-infra     yes                enabled
        """

        Examples: ubuntu release
        | release | next_release | devel_release   |
        | bionic  | focal        | --devel-release |

    @series.xenial
    @series.trusty
    @upgrade
    Scenario Outline: Attached upgrade across LTS releases
            Given a `<release>` machine with ubuntu-advantage-tools installed
            When I attach `contract_token` with sudo
            And I run `apt-get dist-upgrade --assume-yes` with sudo
            And I create the file `/etc/update-manager/release-upgrades.d/ua-test.cfg` with the following
                """
                [Sources]
                AllowThirdParty=yes
                """
            And I run `wget http://archive.ubuntu.com/ubuntu/dists/<next_release>-updates/main/dist-upgrader-all/current/<next_release>.tar.gz -P /tmp/` with sudo
            And I run `tar zxvf /tmp/<next_release>.tar.gz -C /tmp/` with sudo
            And I run `wget https://git.launchpad.net/~chad.smith/ubuntu/+source/ubuntu-release-upgrader/plain/DistUpgrade/DistUpgradeController.py?h=<branch> -O /tmp/DistUpgradeController.py` with sudo
            And I run `wget https://git.launchpad.net/~chad.smith/ubuntu/+source/ubuntu-release-upgrader/plain/data/mirrors.cfg?h=<branch> -O /tmp/mirrors.cfg` with sudo
            And I run `apt remove python3-distupgrade -y` with sudo
            And I run `apt install python3-distro-info -y` with sudo
            Then I verify that running `sh -c "cd /tmp/ && script /home/ubuntu/update.log -c '/tmp/<next_release> --datadir=/tmp --frontend=DistUpgradeViewNonInteractive'"` `with sudo` exits `0`
            When I reboot the `<release>` machine
            And I run `lsb_release -cs` as non-root
            Then I will see the following on stdout:
                """
                <next_release>
                """
            When I run `egrep "<release>|disabled" /etc/apt/sources.list.d/*` as non-root
            Then I will see the following on stdout:
                """
                """
            When I run `ua status` with sudo
            Then stdout matches regexp:
            """
            esm-infra     yes                enabled
            """

            Examples: ubuntu release
            | release | next_release | branch                      |
            | xenial  | bionic       | uru-bionic-ubuntu-advantage |
            | trusty  | xenial       | uru-xenial-ubuntu-advantage |

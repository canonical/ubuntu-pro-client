Feature: UA Install and Uninstall related tests

    @series.all
    @uses.config.machine_type.lxd.container
    Scenario Outline: Do not fail on postinst when cloud-id returns error
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I delete the file `/run/cloud-init/instance-data.json`
        Then I verify that running `dpkg-reconfigure ubuntu-advantage-tools` `with sudo` exits `0`

        Examples: ubuntu release
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | hirsute |

    @series.lts
    @uses.config.contract_token
    @uses.config.machine_type.lxd.container
    Scenario Outline: Purge package after attaching it to a machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `touch /etc/apt/preferences.d/ubuntu-esm-infra` with sudo
        Then I verify that files exist matching `/var/log/ubuntu-advantage.log`
        And I verify that running `test -d /var/lib/ubuntu-advantage` `with sudo` exits `0`
        And I verify that files exist matching `/etc/apt/auth.conf.d/90ubuntu-advantage`
        And I verify that files exist matching `/etc/apt/trusted.gpg.d/ubuntu-advantage-esm-infra-trusty.gpg`
        And I verify that files exist matching `/etc/apt/sources.list.d/ubuntu-esm-infra.list`
        And I verify that files exist matching `/etc/apt/preferences.d/ubuntu-esm-infra`
        When I run `apt-get purge ubuntu-advantage-tools -y` with sudo, retrying exit [100]
        Then stdout matches regexp:
        """
        Purging configuration files for ubuntu-advantage-tools
        """
        And I verify that no files exist matching `/var/log/ubuntu-advantage.log`
        And I verify that no files exist matching `/var/lib/ubuntu-advantage`
        And I verify that no files exist matching `/etc/apt/auth.conf.d/90ubuntu-advantage`
        And I verify that no files exist matching `/etc/apt/sources.list.d/ubuntu-*`
        And I verify that no files exist matching `/etc/apt/trusted.gpg.d/ubuntu-advantage-*`
        And I verify that no files exist matching `/etc/apt/preferences.d/ubuntu-*`

        Examples: ubuntu release
           | release |
           | bionic  |
           | focal   |
           | xenial  |

    @slow
    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Do not fail during postinst with nonstandard python setup
        Given a `<release>` machine with ubuntu-advantage-tools installed
        # Works when in a python virtualenv
        When I run `apt install python3-venv -y` with sudo
        When I run `python3 -m venv env` with sudo
        Then I verify that running `bash -c ". env/bin/activate && python3 -c 'import uaclient'"` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        No module named 'uaclient'
        """
        Then I verify that running `bash -c ". env/bin/activate && dpkg-reconfigure ubuntu-advantage-tools"` `with sudo` exits `0`

        # Works with python built/installed from source
        When I run `wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz` with sudo
        When I run `tar -xvf Python-3.10.0.tgz` with sudo
        When I run `apt install build-essential zlib1g-dev -y` with sudo
        When I run `sh -c "cd Python-3.10.0 && ./configure"` with sudo
        When I run `make -C Python-3.10.0` with sudo
        When I run `make -C Python-3.10.0 install` with sudo
        When I run `python3 --version` with sudo
        Then I will see the following on stdout
        """
        Python 3.10.0
        """
        Then I verify that running `python3 -c "import uaclient"` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        No module named 'uaclient'
        """
        Then I verify that running `dpkg-reconfigure ubuntu-advantage-tools` `with sudo` exits `0`

        # Works even when user overwrites /usr/bin/python3 with their version
        When I run `ln -sf /usr/local/bin/python3.10 /usr/bin/python3` with sudo
        Then I verify that running `/usr/bin/python3 -c "import uaclient"` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        No module named 'uaclient'
        """
        Then I verify that running `dpkg-reconfigure ubuntu-advantage-tools` `with sudo` exits `0`

        Examples: ubuntu release
           | release | deadsnakes-pkg | deadsnakes-version |
           | xenial  | python3.9      | 3.9.4              |
           | bionic  | python3.9      | 3.9.7              |
           | focal   | python3.9      | 3.9.7              |
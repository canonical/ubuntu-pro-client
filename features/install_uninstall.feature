Feature: Pro Install and Uninstall related tests

    Scenario Outline: Do not fail on postinst when cloud-id returns error
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I delete the file `/run/cloud-init/instance-data.json`
        Then I verify that running `dpkg-reconfigure ubuntu-advantage-tools` `with sudo` exits `0`

        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

    @uses.config.contract_token
    Scenario Outline: Purge package after attaching it to a machine
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token` with sudo
        And I run `touch /etc/apt/preferences.d/ubuntu-esm-infra` with sudo
        Then I verify that files exist matching `/var/log/ubuntu-advantage.log`
        And I verify that running `test -d /var/lib/ubuntu-advantage` `with sudo` exits `0`
        And I verify that files exist matching `/etc/apt/auth.conf.d/90ubuntu-advantage`
        And I verify that files exist matching `/etc/apt/trusted.gpg.d/ubuntu-pro-esm-infra.gpg`
        And I verify that files exist matching `/etc/apt/sources.list.d/ubuntu-esm-infra.list`
        And I verify that files exist matching `/etc/apt/preferences.d/ubuntu-esm-infra`
        When I run `apt purge ubuntu-advantage-tools -y` with sudo, retrying exit [100]
        Then stdout matches regexp:
        """
        Purging configuration files for ubuntu-advantage-tools
        """
        And I verify that no files exist matching `/var/log/ubuntu-advantage.log`
        And I verify that no files exist matching `/var/lib/ubuntu-advantage`
        And I verify that no files exist matching `/etc/apt/auth.conf.d/90ubuntu-advantage`
        And I verify that no files exist matching `/etc/apt/sources.list.d/ubuntu-*`
        And I verify that no files exist matching `/etc/apt/trusted.gpg.d/ubuntu-pro-*`
        And I verify that no files exist matching `/etc/apt/preferences.d/ubuntu-*`

        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    @slow
    Scenario Outline: Do not fail during postinst with nonstandard python setup
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        # Works when in a python virtualenv
        When I apt update
        And I apt install `python3-venv`
        And I run `python3 -m venv env` with sudo
        Then I verify that running `bash -c ". env/bin/activate && python3 -c 'import uaclient'"` `with sudo` exits `1`
        Then stderr matches regexp:
        """
        No module named 'uaclient'
        """
        Then I verify that running `bash -c ". env/bin/activate && dpkg-reconfigure ubuntu-advantage-tools"` `with sudo` exits `0`

        # Works with python built/installed from source
        When I run `wget https://www.python.org/ftp/python/3.10.0/Python-3.10.0.tgz` with sudo
        When I run `tar -xvf Python-3.10.0.tgz` with sudo
        When I apt install `build-essential zlib1g-dev`
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

        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |

    @skip.install_from.local
    @skip.install_from.prebuilt
    Scenario Outline: ubuntu-pro-client brings up-to-date ubuntu-advantage-tools
        Given a `<release>` `<machine_type>` machine
        When I set up the apt source for ubuntu-advantage-tools
        When I apt install `ubuntu-pro-client`
        Then I verify that the version of `ubuntu-pro-client` equals the version of `ubuntu-advantage-tools`
        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | lxd-container |
           | bionic  | lxd-container |
           | focal   | lxd-container |
           | jammy   | lxd-container |
           | mantic  | lxd-container |

    @skip.install_from.local
    @skip.install_from.prebuilt
    Scenario Outline: ubuntu-pro-image-auto-attach brings up-to-date ubuntu-advantage-pro
        Given a `<release>` `<machine_type>` machine
        When I set up the apt source for ubuntu-advantage-tools
        When I apt install `ubuntu-pro-image-auto-attach`
        Then I verify that the version of `ubuntu-pro-image-auto-attach` equals the version of `ubuntu-advantage-pro`
        Examples: ubuntu release
           | release | machine_type  |
           | xenial  | aws.pro       |
           | bionic  | aws.pro       |
           | focal   | aws.pro       |
           | jammy   | aws.pro       |
           | mantic  | aws.pro       |

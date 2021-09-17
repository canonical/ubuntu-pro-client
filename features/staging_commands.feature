@uses.config.contract_token_staging
Feature: Enable command behaviour when attached to an UA staging subscription

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable esm-apps on a machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt-cache policy` as non-root
        Then apt-cache policy for the following url has permission `500`
        """
        https://esm.staging.ubuntu.com/apps/ubuntu <release>-apps-updates/main amd64 Packages
        """
        And apt-cache policy for the following url has permission `500`
        """
        https://esm.staging.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        And I verify that running `apt update` `with sudo` exits `0`
        When I run `apt install -y <apps-pkg>` with sudo, retrying exit [100]
        And I run `apt-cache policy <apps-pkg>` as non-root
        Then stdout matches regexp:
        """
        Version table:
        \s*\*\*\* .* 500
        \s*500 https://esm.staging.ubuntu.com/apps/ubuntu <release>-apps-security/main amd64 Packages
        """
        When I run `mkdir -p /var/lib/ubuntu-advantage/messages` with sudo
        When I create the file `/var/lib/ubuntu-advantage/messages/apt-pre-invoke-no-packages-infra.tmpl` with the following
        """
        esm-infra-no {ESM_INFRA_PKG_COUNT}:{ESM_INFRA_PACKAGES}
        """
        When I create the file `/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-infra.tmpl` with the following
        """
        esm-infra {ESM_INFRA_PKG_COUNT}:{ESM_INFRA_PACKAGES}
        """
        When I create the file `/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-apps.tmpl` with the following
        """
        esm-apps {ESM_APPS_PKG_COUNT}:{ESM_APPS_PACKAGES}
        """
        When I create the file `/var/lib/ubuntu-advantage/messages/apt-pre-invoke-no-packages-apps.tmpl` with the following
        """
        esm-apps-no {ESM_APPS_PKG_COUNT}:{ESM_APPS_PACKAGES}
        """
        When I run `/usr/lib/ubuntu-advantage/apt-esm-hook process-templates` with sudo
        When I run `cat /var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-apps` with sudo
        Then stdout matches regexp:
        """
        esm-apps(-no)? \d+:(.*)?
        """
        When I run `cat /var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-infra` with sudo
        Then stdout matches regexp:
        """
        esm-infra(-no)? \d+:(.*)?
        """
        When I create the file `/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-infra.tmpl` with the following
        """
        esm-infra {ESM_INFRA_PKG_COUNT} {ESM_INFRA_PACKAGES}
        """
        When I create the file `/var/lib/ubuntu-advantage/messages/apt-pre-invoke-no-packages-infra.tmpl` with the following
        """
        esm-infra-no {ESM_INFRA_PKG_COUNT} {ESM_INFRA_PACKAGES}
        """
        When I create the file `/var/lib/ubuntu-advantage/messages/apt-pre-invoke-packages-apps.tmpl` with the following
        """
        esm-apps {ESM_APPS_PKG_COUNT} {ESM_APPS_PACKAGES}
        """
        When I run `apt upgrade --dry-run` with sudo
        Then stdout matches regexp:
        """
        esm-apps(-no)? \d+.*

        esm-infra(-no)? \d+.*
        """
        When I verify that running `ua enable esm-apps` `with sudo` exits `1`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        UA Apps: ESM is already enabled.
        See: sudo ua status
        """

        Examples: ubuntu release
           | release | apps-pkg |
           | bionic  | bundler  |
           | focal   | ant      |
           | xenial  | jq       |

    @series.lts
    @uses.config.machine_type.lxd.container
    Scenario Outline: Attached enable ros on a machine
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I attach `contract_token_staging` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                disabled           Security Updates for the Robot Operating System
        """
        When I run `ua enable ros --assume-yes --beta` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        """
        And stdout matches regexp
        """
        esm-infra     yes                enabled            UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I verify that running `ua disable esm-apps` `with sudo` and stdin `N` exits `1`
        Then stdout matches regexp
        """
        ROS ESM Security Updates depends on UA Apps: ESM.
        Disable ROS ESM Security Updates and proceed to disable UA Apps: ESM\? \(y\/N\) Cannot disable UA Apps: ESM when ROS ESM Security Updates is enabled.
        """
        When I run `ua disable esm-apps` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        ROS ESM Security Updates depends on UA Apps: ESM.
        Disable ROS ESM Security Updates and proceed to disable UA Apps: ESM\? \(y\/N\) Disabling dependent service: ROS ESM Security Updates
        Updating package lists
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                disabled           Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                disabled           UA Apps: Extended Security Maintenance \(ESM\)
        """
        When I verify that running `ua enable ros --beta` `with sudo` and stdin `N` exits `1`
        Then stdout matches regexp
        """
        ROS ESM Security Updates cannot be enabled with UA Apps: ESM disabled.
        Enable UA Apps: ESM and proceed to enable ROS ESM Security Updates\? \(y\/N\) Cannot enable ROS ESM Security Updates when UA Apps: ESM is disabled.
        """

        When I run `ua enable ros --beta` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        ROS ESM Security Updates cannot be enabled with UA Apps: ESM disabled.
        Enable UA Apps: ESM and proceed to enable ROS ESM Security Updates\? \(y\/N\) Enabling required service: UA Apps: ESM
        UA Apps: ESM enabled
        Updating package lists
        ROS ESM Security Updates enabled
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        """
        And stdout matches regexp
        """
        esm-infra     yes                enabled            UA Infra: Extended Security Maintenance \(ESM\)
        """
        When I run `apt-cache policy` as non-root
        Then apt-cache policy for the following url has permission `500`
        """
        <ros-security-source> amd64 Packages
        """
        When I run `apt install python3-catkin-pkg -y` with sudo
        Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-security-source>`

        When I run `ua enable ros-updates --assume-yes --beta` with sudo
        And I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros-updates   yes                enabled            All Updates for the Robot Operating System
        """
        When I run `apt-cache policy` as non-root
        Then apt-cache policy for the following url has permission `500`
        """
        <ros-updates-source> amd64 Packages
        """
        When I run `apt install python3-catkin-pkg -y` with sudo
        Then I verify that `python3-catkin-pkg` is installed from apt source `<ros-updates-source>`
        When I run `ua disable ros` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        ROS ESM All Updates depends on ROS ESM Security Updates.
        Disable ROS ESM All Updates and proceed to disable ROS ESM Security Updates\? \(y\/N\) Disabling dependent service: ROS ESM All Updates
        Updating package lists
        """
        When I run `ua enable ros-updates --beta` `with sudo` and stdin `y`
        Then stdout matches regexp
        """
        One moment, checking your subscription first
        ROS ESM All Updates cannot be enabled with ROS ESM Security Updates disabled.
        Enable ROS ESM Security Updates and proceed to enable ROS ESM All Updates\? \(y\/N\) Enabling required service: ROS ESM Security Updates
        ROS ESM Security Updates enabled
        Updating package lists
        ROS ESM All Updates enabled
        """
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros-updates   yes                enabled            All Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        When I run `ua disable ros-updates --assume-yes` with sudo
        When I run `ua disable ros --assume-yes` with sudo
        When I run `ua disable esm-apps --assume-yes` with sudo
        When I run `ua disable esm-infra --assume-yes` with sudo
        When I run `ua enable ros-updates --assume-yes --beta` with sudo
        When I run `ua status --all` as non-root
        Then stdout matches regexp
        """
        ros-updates   yes                enabled            All Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        ros           yes                enabled            Security Updates for the Robot Operating System
        """
        And stdout matches regexp
        """
        esm-apps      yes                enabled            UA Apps: Extended Security Maintenance \(ESM\)
        """
        And stdout matches regexp
        """
        esm-infra     yes                enabled            UA Infra: Extended Security Maintenance \(ESM\)
        """

        Examples: ubuntu release
           | release | ros-security-source                                            | ros-updates-source                                                    |
           | xenial  | https://esm.staging.ubuntu.com/ros/ubuntu xenial-security/main | https://esm.staging.ubuntu.com/ros-updates/ubuntu xenial-updates/main |
           | bionic  | https://esm.staging.ubuntu.com/ros/ubuntu bionic-security/main | https://esm.staging.ubuntu.com/ros-updates/ubuntu bionic-updates/main |

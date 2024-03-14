@uses.config.contract_token
Feature: Performing attach using ua-airgapped

    Scenario Outline: Pro works with the airgapped contract server
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        # set up the apt mirror configuration
        Given a `jammy` `<machine_type>` machine named `mirror`
        When I run `add-apt-repository ppa:yellow/ua-airgapped -y` `with sudo` on the `mirror` machine
        And I apt update on the `mirror` machine
        And I apt install `apt-mirror get-resource-tokens ua-airgapped` on the `mirror` machine
        And I download the service credentials on the `mirror` machine
        And I extract the `esm-infra` credentials from the `mirror` machine
        And I extract the `esm-apps` credentials from the `mirror` machine
        And I set the apt-mirror file for `<release>` with the `esm-infra,esm-apps` credentials on the `mirror` machine
        And I run `apt-mirror` `with sudo` on the `mirror` machine
        And I serve the `esm-infra` mirror using port `8000` on the `mirror` machine
        And I serve the `esm-apps` mirror using port `9000` on the `mirror` machine
        # set up the ua-airgapped configuration
        And I create the contract config overrides file for `esm-infra,esm-apps` on the `mirror` machine
        And I generate the contracts-airgapped configuration on the `mirror` machine
        # set up the contracts-airgapped configuration
        Given a `jammy` `<machine_type>` machine named `contracts`
        When I run `add-apt-repository ppa:yellow/ua-airgapped -y` `with sudo` on the `contracts` machine
        And I apt update on the `contracts` machine
        And I apt install `contracts-airgapped` on the `contracts` machine
        And I run `apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 4067E40313CB4B13` `with sudo` on the `contracts` machine
        And I disable any internet connection on the `contracts` machine
        And I send the contracts-airgapped config from the `mirror` machine to the `contracts` machine
        And I start the contracts-airgapped service on the `contracts` machine
        # attach an airgapped machine to the contracts-airgapped server
        And I disable any internet connection on the machine
        And I change config key `contract_url` to use value `http://$behave_var{machine-ip contracts}:8484`
        And I attach `contract_token` with sudo
        Then I verify that `esm-infra` is enabled
        And I verify that `esm-apps` is enabled
        When I run `apt-cache policy hello` with sudo
        Then stdout matches regexp:
        """
        510 .*:9000/ubuntu jammy-apps-security/main
        """
        And stdout matches regexp:
        """
        510 .*:8000/ubuntu jammy-infra-security/main
        """
        Then I verify that running `pro refresh` `with sudo` exits `0`

        Examples: ubuntu release
            | release | machine_type  |
            | jammy   | lxd-container |

    Scenario Outline: airgapped environment with same apt url for different services
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
        # set up the apt mirror configuration
        Given a `jammy` `<machine_type>` machine named `mirror`
        When I run `add-apt-repository ppa:yellow/ua-airgapped -y` `with sudo` on the `mirror` machine
        And I run `apt-get update` `with sudo` on the `mirror` machine
        And I run `apt-get install apt-mirror get-resource-tokens ua-airgapped -yq` `with sudo` on the `mirror` machine
        And I download the service credentials on the `mirror` machine
        And I extract the `esm-infra` credentials from the `mirror` machine
        And I extract the `esm-apps` credentials from the `mirror` machine
        And I set the apt-mirror file for `<release>` with the `esm-infra,esm-apps` credentials on the `mirror` machine
        And I run `apt-mirror` `with sudo` on the `mirror` machine
        And I consolidate `esm-infra,esm-apps` on a single mirror on the `mirror` machine
        And I serve the `all-mirrors` mirror using port `8000` on the `mirror` machine
        # set up the ua-airgapped configuration
        And I create the contract config overrides file for `esm-infra,esm-apps` on the `mirror` machine
        And I generate the contracts-airgapped configuration on the `mirror` machine
        # set up the contracts-airgapped configuration
        Given a `jammy` `<machine_type>` machine named `contracts`
        When I run `add-apt-repository ppa:yellow/ua-airgapped -y` `with sudo` on the `contracts` machine
        And I run `apt-get update` `with sudo` on the `contracts` machine
        And I run `apt-get install contracts-airgapped -yq` `with sudo` on the `contracts` machine
        And I run `apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 4067E40313CB4B13` `with sudo` on the `contracts` machine
        And I disable any internet connection on the `contracts` machine
        And I send the contracts-airgapped config from the `mirror` machine to the `contracts` machine
        And I start the contracts-airgapped service on the `contracts` machine
        # attach an airgapped machine to the contracts-airgapped server
        And I disable any internet connection on the machine
        And I change config key `contract_url` to use value `http://$behave_var{machine-ip contracts}:8484`
        And I attach `contract_token` with sudo
        Then stdout matches regexp:
        """
        esm-apps     +yes      +enabled .*
        esm-infra    +yes      +enabled .*
        """
        When I run `apt-cache policy hello` with sudo
        Then stdout matches regexp:
        """
        510 .*:8000/ubuntu jammy-apps-security/main
        """
        And stdout matches regexp:
        """
        510 .*:8000/ubuntu jammy-infra-security/main
        """
        Then I verify that running `pro refresh` `with sudo` exits `0`

        Examples: ubuntu release
            | release | machine_type  |
            | jammy   | lxd-container |

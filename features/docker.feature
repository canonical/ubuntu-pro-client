@uses.config.contract_token
Feature: Build docker images with pro services

    @slow
    @docker
    @series.focal
    @uses.config.machine_type.lxd.vm
    Scenario Outline: Build docker images with pro services
        Given a `focal` machine with ubuntu-advantage-tools installed
        When I have the `<container_release>` debs under test in `/home/ubuntu`
        When I run `apt-get install -y docker.io jq` with sudo
        When I create the file `/home/ubuntu/Dockerfile` with the following:
        """
        FROM ubuntu:<container_release>

        COPY ./ubuntu-advantage-tools.deb /ua.deb

        RUN --mount=type=secret,id=ua-attach-config \
            apt-get update \
            && apt-get install --no-install-recommends -y ubuntu-advantage-tools ca-certificates \

            && dpkg -i /ua.deb \

            && apt-get install -f \

            && pro attach --attach-config /run/secrets/ua-attach-config \

            # Normally an apt upgrade is recommended, but we dont do that here
            # in order to measure the image size bloat from just the enablement
            # process
            # && apt-get upgrade -y \

            && apt-get install -y <test_package_name> \

            # If you need ca-certificates, remove it from this line
            && apt-get purge --auto-remove -y ubuntu-advantage-tools ca-certificates \

            && rm -rf /var/lib/apt/lists/*
        """
        When I create the file `/home/ubuntu/ua-attach-config.yaml` with the following:
        """
        token: <contract_token>
        enable_services: <enable_services>
        """
        When I replace `<contract_token>` in `/home/ubuntu/ua-attach-config.yaml` with token `contract_token`

        # Build succeeds
        When I run shell command `DOCKER_BUILDKIT=1 docker build . --secret id=ua-attach-config,src=ua-attach-config.yaml -t ua-test` with sudo

        # Bloat is minimal (new size == original size + deb size + test package size)
        Then docker image `ua-test` is not significantly larger than `ubuntu:<container_release>` with `<test_package_name>` installed

        # No secrets or artifacts leftover
        Then `90ubuntu-advantage` is not present in any docker image layer
        Then `machine-token.json` is not present in any docker image layer
        Then `ubuntu-advantage.log` is not present in any docker image layer
        Then `uaclient.conf` is not present in any docker image layer

        # Service successfully enabled (Correct version of package installed)
        When I run `docker run ua-test dpkg-query --showformat='${Version}' --show <test_package_name>` with sudo
        Then stdout matches regexp:
        """
        <test_package_version>
        """

        # Invalid attach config file causes build to fail
        When I create the file `/home/ubuntu/ua-attach-config.yaml` with the following:
        """
        token: <contract_token>
        enable_services: { fips: true }
        """
        When I replace `<contract_token>` in `/home/ubuntu/ua-attach-config.yaml` with token `contract_token`
        Then I verify that running `DOCKER_BUILDKIT=1 docker build . --no-cache --secret id=ua-attach-config,src=ua-attach-config.yaml -t ua-test` `with sudo` exits `1`

        Examples: ubuntu release
           | release | container_release |enable_services | test_package_name | test_package_version |
           | focal   | xenial            | [ esm-infra ]  | curl              | esm                  |
           | focal   | bionic            | [ fips ]       | openssl           | fips                 |
           | focal   | focal             | [ esm-apps ]   | hello             | esm                  |

Feature: Build docker images with pro services

  @slow @uses.config.contract_token
  Scenario Outline: Build docker images with pro services
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I have the `<container_release>` debs under test in `/home/ubuntu`
    When I apt install `docker.io docker-buildx jq`
    When I create the file `/home/ubuntu/Dockerfile` with the following:
      """
      FROM ubuntu:<container_release>

      COPY ./ubuntu-advantage-tools.deb /ua.deb
      COPY ./ubuntu-pro-client.deb /pro.deb

      RUN --mount=type=secret,id=ua-attach-config \
          apt-get update \
          && apt-get install --no-install-recommends -y ubuntu-advantage-tools ca-certificates \

          && ((apt install /ua.deb /pro.deb -y || true)) \

          && apt-get install -f \

          && pro attach --attach-config /run/secrets/ua-attach-config \

          # Normally an apt upgrade is recommended, but we dont do that here
          # in order to measure the image size bloat from just the enablement
          # process
          # && apt-get upgrade -y \

          && apt-get install -y <test_package_name> \

          # If you need ca-certificates, remove it from this line
          && apt-get purge --auto-remove -y ubuntu-advantage-tools ubuntu-pro-client ca-certificates \

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
      | release  | machine_type | container_release | enable_services | test_package_name | test_package_version |
      | noble    | lxd-vm       | xenial            | [ esm-infra ]   | curl              | esm                  |
      | noble    | lxd-vm       | bionic            | [ fips ]        | openssl           | fips                 |
      | noble    | lxd-vm       | focal             | [ esm-apps ]    | hello             | esm                  |
      | oracular | lxd-vm       | xenial            | [ esm-infra ]   | curl              | esm                  |
      | oracular | lxd-vm       | bionic            | [ fips ]        | openssl           | fips                 |
      | oracular | lxd-vm       | focal             | [ esm-apps ]    | hello             | esm                  |

  Scenario Outline: Build pro docker images auto-attached instances - settings_overrides method
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I have the `<container_release>` debs under test in `/home/ubuntu`
    When I run `apt-get update` with sudo
    When I apt install `docker.io docker-buildx`
    When I create the file `/home/ubuntu/Dockerfile` with the following:
      """
      FROM ubuntu:<container_release>
      ARG PRO_CLOUD_OVERRIDE=

      COPY ./ubuntu-advantage-tools.deb /ua.deb
      COPY ./ubuntu-pro-client.deb /pro.deb

      RUN --mount=type=secret,id=ua-attach-config \
          apt-get update \
          && apt-get install --no-install-recommends -y ubuntu-advantage-tools ca-certificates \

          && ((apt install /ua.deb /pro.deb -y || true)) \

          && apt-get install -f \

          && echo "settings_overrides: { cloud_type: $PRO_CLOUD_OVERRIDE }" >> /etc/ubuntu-advantage/uaclient.conf \
          && pro api u.pro.attach.auto.full_auto_attach.v1 --data '{"enable": <enable_services>}' \

          && apt-get install -y <test_package_name> \

          # If you need ca-certificates, remove it from this line
          && apt-get purge --auto-remove -y ubuntu-advantage-tools ubuntu-pro-client ca-certificates \

          && rm -rf /var/lib/apt/lists/*
      """
    # Build succeeds
    When I run shell command `DOCKER_BUILDKIT=1 docker build . -t test --build-arg PRO_CLOUD_OVERRIDE=<cloud_override> <extra_build_args>` with sudo
    # Service successfully enabled (Correct version of package installed)
    When I run `docker run test dpkg-query --showformat='${Version}' --show <test_package_name>` with sudo
    Then stdout matches regexp:
      """
      <test_package_version>
      """

    Examples: ubuntu release
      | release | machine_type | cloud_override | container_release | enable_services | test_package_name | test_package_version | extra_build_args |
      | jammy   | aws.pro      | aws            | xenial            | [ "esm-infra" ] | curl              | esm                  | --network=host   |
      | jammy   | azure.pro    | azure          | bionic            | [ "fips" ]      | openssl           | fips                 |                  |
      | jammy   | gcp.pro      | gce            | focal             | [ "esm-apps" ]  | hello             | esm                  |                  |

  Scenario Outline: Build pro docker images auto-attached instances - API arg method
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I have the `<container_release>` debs under test in `/home/ubuntu`
    When I run `apt-get update` with sudo
    When I apt install `docker.io docker-buildx`
    When I create the file `/home/ubuntu/Dockerfile` with the following:
      """
      FROM ubuntu:<container_release>
      ARG PRO_CLOUD_OVERRIDE=

      COPY ./ubuntu-advantage-tools.deb /ua.deb
      COPY ./ubuntu-pro-client.deb /pro.deb

      RUN --mount=type=secret,id=ua-attach-config \
          apt-get update \
          && apt-get install --no-install-recommends -y ubuntu-advantage-tools ca-certificates \

          && ((apt install /ua.deb /pro.deb -y || true)) \

          && apt-get install -f \

          && pro --debug api u.pro.attach.auto.full_auto_attach.v1 --data "{\"cloud_override\": \"$PRO_CLOUD_OVERRIDE\", \"enable\": [\"<enable_service>\"]}" \

          && apt-get install -y <test_package_name> \

          # If you need ca-certificates, remove it from this line
          && apt-get purge --auto-remove -y ubuntu-advantage-tools ubuntu-pro-client ca-certificates \

          && rm -rf /var/lib/apt/lists/*
      """
    # Build succeeds
    When I run shell command `DOCKER_BUILDKIT=1 docker build . -t test --build-arg PRO_CLOUD_OVERRIDE=<cloud_override> <extra_build_args>` with sudo
    # Service successfully enabled (Correct version of package installed)
    When I run `docker run test dpkg-query --showformat='${Version}' --show <test_package_name>` with sudo
    Then stdout matches regexp:
      """
      <test_package_version>
      """

    Examples: ubuntu release
      | release | machine_type | cloud_override | container_release | enable_service | test_package_name | test_package_version | extra_build_args |
      | jammy   | aws.pro      | aws            | xenial            | esm-infra      | curl              | esm                  | --network=host   |
      | jammy   | azure.pro    | azure          | bionic            | fips           | openssl           | fips                 |                  |
      | jammy   | gcp.pro      | gce            | focal             | esm-apps       | hello             | esm                  |                  |

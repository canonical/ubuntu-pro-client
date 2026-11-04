Feature: Docker layer scanning harness

  Scenario Outline: Find a file removed in a later Docker layer
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I apt install `docker.io`
    When I create the file `/home/ubuntu/Dockerfile.layer-control` with the following:
      """
      FROM ubuntu:<release>
      RUN touch /90ubuntu-advantage /persistent-control-marker
      RUN rm /90ubuntu-advantage
      RUN touch /same-layer-control-marker && rm /same-layer-control-marker
      """
    When I run shell command `docker build -f Dockerfile.layer-control -t docker-layer-control .` with sudo
    When I run `docker run --rm docker-layer-control test ! -e /90ubuntu-advantage` with sudo
    When I run `docker run --rm docker-layer-control test -e /persistent-control-marker` with sudo
    Then the following files are present in any layer of docker image `docker-layer-control`
      | file_name                 |
      | 90ubuntu-advantage        |
      | persistent-control-marker |
    Then the following files are not present in any layer of docker image `docker-layer-control`
      | file_name                 |
      | same-layer-control-marker |

    Examples: ubuntu release
      | release  | machine_type |
      | bionic   | lxd-vm       |
      | focal    | lxd-vm       |
      | jammy    | lxd-vm       |
      | noble    | lxd-vm       |
      | resolute | lxd-vm       |

Feature: Pro Client help text

  Scenario Outline: Help text for the Pro Client commands
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro collect-logs --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro collect-logs \[flags\]

      Collect logs and relevant system information into a tarball.

      (optional arguments|options):
        -h, --help            show this help message and exit
        -o OUTPUT, --output OUTPUT
                              tarball where the logs will be stored. \(Defaults to
                              ./pro_logs.tar.gz\)
      """
    When I run `pro api --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro api \[flags\]

      Calls the Client API endpoints.

      positional arguments:
        endpoint              API endpoint to call

      (optional arguments|options):
        -h, --help            show this help message and exit
        --show-progress       For endpoints that support progress updates, show each(.|\n)*
                              progress update on a new line in JSON format
        --args \[OPTIONS .*\](.|\n)*Options to pass to the API endpoint, formatted as(.|\n)*
                              key=value
        --data DATA           arguments in JSON format to the API endpoint
      """
    When I run `pro disable --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro disable \[flags\]

      Disable an Ubuntu Pro service.

      positional arguments:
        service              the name\(s\) of the Ubuntu Pro services to disable. One
                             of: anbox-cloud, cc-eal, cis, esm-apps, esm-infra,
                             fips, fips-preview, fips-updates, landscape, livepatch,
                             realtime-kernel, ros, ros-updates

      (optional arguments|options):
        -h, --help           show this help message and exit
        --assume-yes         do not prompt for confirmation before performing the
                             disable
        --format \{cli,json\}  output in the specified format \(default: cli\)
        --purge              disable the service and remove/downgrade related
                             packages \(experimental\)
      """
    When I run `pro enable --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro enable \[flags\]

      Enable an Ubuntu Pro service.

      positional arguments:
        service              the name\(s\) of the Ubuntu Pro services to enable. One
                             of: anbox-cloud, cc-eal, cis, esm-apps, esm-infra,
                             fips, fips-preview, fips-updates, landscape, livepatch,
                             realtime-kernel, ros, ros-updates

      (optional arguments|options):
        -h, --help           show this help message and exit
        --assume-yes         do not prompt for confirmation before performing the
                             enable
        --access-only        do not auto-install packages. Valid for cc-eal, cis and
                             realtime-kernel.
        --beta               allow beta service to be enabled
        --format \{cli,json\}  output in the specified format \(default: cli\)
        --variant VARIANT    The name of the variant to use when enabling the
                             service
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

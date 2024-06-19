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

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

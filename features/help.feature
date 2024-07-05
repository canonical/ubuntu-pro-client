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
    When I run `pro attach --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro attach \[flags\]

      Attach this machine to an Ubuntu Pro subscription with a token obtained from:
      https://ubuntu.com/pro/dashboard

      When running this command without a token, it will generate a short code
      and prompt you to attach the machine to your Ubuntu Pro account using
      a web browser.

      positional arguments:
        token                 token obtained for Ubuntu Pro authentication

      (optional arguments|options):
        -h, --help            show this help message and exit
        --no-auto-enable      do not enable any recommended services automatically
        --attach-config ATTACH_CONFIG
                              use the provided attach config file instead of passing
                              the token on the cli
        --format \{cli,json\}   output in the specified format \(default: cli\)
      """
    When I run `pro auto-attach --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro auto-attach \[flags\]

      Automatically attach on an Ubuntu Pro cloud instance.

      (optional arguments|options):
        -h, --help  show this help message and exit
      """
    When I run `pro detach --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro detach \[flags\]

      Detach this machine from an Ubuntu Pro subscription.

      (optional arguments|options):
        -h, --help           show this help message and exit
        --assume-yes         do not prompt for confirmation before performing the
                             detach
        --format \{cli,json\}  output in the specified format \(default: cli\)
      """
    When I run `pro security-status --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro security-status \[flags\]

      Show security updates for packages in the system, including all
      available Expanded Security Maintenance \(ESM\) related content.

      Shows counts of how many packages are supported for security updates
      in the system.

      If called with --format json\|yaml it shows a summary of the
      installed packages based on the origin:
      - main/restricted/universe/multiverse: packages from the Ubuntu archive
      - esm-infra/esm-apps: packages from the ESM archive
      - third-party: packages installed from non-Ubuntu sources
      - unknown: packages which don't have an installation source \(like local
        deb packages or packages for which the source was removed\)

      The output contains basic information about Ubuntu Pro. For a
      complete status on Ubuntu Pro services, run 'pro status'.

      (optional arguments|options):
        -h, --help            show this help message and exit
        --format \{json,yaml,text\}
                              output in the specified format \(default: text\)
        --thirdparty          List and present information about third-party
                              packages
        --unavailable         List and present information about unavailable
                              packages
        --esm-infra           List and present information about esm-infra packages
        --esm-apps            List and present information about esm-apps packages
      """
    When I run `pro fix --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro fix \[flags\]

      Inspect and resolve CVEs and USNs \(Ubuntu Security Notices\) on this machine.

      positional arguments:
        security_issue  Security vulnerability ID to inspect and resolve on this
                        system. Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-
                        dd

      (optional arguments|options):
        -h, --help      show this help message and exit
        --dry-run       If used, fix will not actually run but will display
                        everything that will happen on the machine during the
                        command.
        --no-related    If used, when fixing a USN, the command will not try to also
                        fix related USNs to the target USN.
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

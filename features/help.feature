Feature: Pro Client help text

  Scenario Outline: Help text for the Pro Client commands
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro collect-logs --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro collect-logs \[-h\] \[-o OUTPUT\]

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
      usage: pro api \[-h\] \[--show-progress\] \[--args \[OPTIONS ...\]\] \[--data DATA\]
                     endpoint

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
      usage: pro disable \[-h\] \[--assume-yes\] \[--format \{cli,json\}\] \[--purge\]
                         service \[service ...\]

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
      usage: pro enable \[-h\] \[--assume-yes\] \[--access-only\] \[--beta\]
                        \[--format \{cli,json\}\] \[--variant VARIANT\]
                        service \[service ...\]

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
      usage: pro attach \[-h\] \[--no-auto-enable\] \[--attach-config ATTACH_CONFIG\]
                        \[--format \{cli,json\}\]
                        \[token\]

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
      usage: pro auto-attach \[-h\]

      Automatically attach on an Ubuntu Pro cloud instance.

      (optional arguments|options):
        -h, --help  show this help message and exit
      """
    When I run `pro detach --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro detach \[-h\] \[--assume-yes\] \[--format \{cli,json\}\]

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
      usage: pro security-status \[-h\] \[--format \{json,yaml,text\}\]
                                 \[--thirdparty \| --unavailable \| --esm-infra \| --esm-apps\]

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
      usage: pro fix \[-h\] \[--dry-run\] \[--no-related\] security_issue

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
    When I run `pro status --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro status \[-h\] \[--wait\] \[--format \{tabular,json,yaml\}\]
                        \[--simulate-with-token TOKEN\] \[--all\]

      Report current status of Ubuntu Pro services on system.

      This shows whether this machine is attached to an Ubuntu Advantage
      support contract. When attached, the report includes the specific
      support contract details including contract name, expiry dates, and the
      status of each service on this system.

      The attached status output has four columns:

      \* SERVICE: name of the service
      \* ENTITLED: whether the contract to which this machine is attached
        entitles use of this service. Possible values are: yes or no
      \* STATUS: whether the service is enabled on this machine. Possible
        values are: enabled, disabled, n/a \(if your contract entitles
        you to the service, but it isn't available for this machine\) or — \(if
        you aren't entitled to this service\)
      \* DESCRIPTION: a brief description of the service

      The unattached status output instead has three columns. SERVICE
      and DESCRIPTION are the same as above, and there is the addition
      of:

      \* AVAILABLE: whether this service would be available if this machine
        were attached. The possible values are yes or no.

      If --simulate-with-token is used, then the output has five
      columns. SERVICE, AVAILABLE, ENTITLED and DESCRIPTION are the same
      as mentioned above, and AUTO_ENABLED shows whether the service is set
      to be enabled when that token is attached.

      If the --all flag is set, beta and unavailable services are also
      listed in the output.

      (optional arguments|options):
        -h, --help            show this help message and exit
        --wait                Block waiting on pro to complete
        --format \{tabular,json,yaml\}
                              output in the specified format \(default: tabular\)
        --simulate-with-token TOKEN
                              simulate the output status using a provided token
        --all                 Include unavailable and beta services
      """
    When I run `pro refresh --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro refresh \[-h\] \[\{contract,config,messages\}\]

      Refresh three distinct Ubuntu Pro related artifacts in the system:

      \* contract: Update contract details from the server.
      \* config:   Reload the config file.
      \* messages: Update APT and MOTD messages related to UA.

      You can individually target any of the three specific actions,
      by passing the target name to the command.  If no `target`
      is specified, all targets are refreshed.

      positional arguments:
        \{contract,config,messages\}
                              Target to refresh.

      (optional arguments|options):
        -h, --help            show this help message and exit
      """
    When I run `pro system --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro system \[-h\]  ...

      Output system related information related to Pro services

      (optional arguments|options):
        -h, --help       show this help message and exit

      Available Commands:
       *
          reboot-required
                         does the system need to be rebooted
      """
    When I run `pro system reboot-required --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro system reboot-required \[-h\]

      Report the current reboot-required status for the machine.

      This command will output one of the three following states
      for the machine regarding reboot:

      \* no: The machine doesn't require a reboot
      \* yes: The machine requires a reboot
      \* yes-kernel-livepatches-applied: There are only kernel related
        packages that require a reboot, but Livepatch has already provided
        patches for the current running kernel. The machine still needs a
        reboot, but you can assess if the reboot can be performed in the
        nearest maintenance window.
      """
    When I run `pro config --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro config \[-h\]  ...

      Manage Ubuntu Pro configuration

      (optional arguments|options):
        -h, --help  show this help message and exit

      Available Commands:
       *
          show      Show customizable configuration settings
          set       Set and apply Ubuntu Pro configuration settings
          unset     Unset Ubuntu Pro configuration setting
      """
    When I run `pro config show --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro config show \[-h\] \[key\]

      Show customizable configuration settings

      positional arguments:
        key         Optional key or key\(s\) to show configuration settings.
      """
    When I run `pro config set --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro config set \[-h\] key_value_pair

      Set and apply Ubuntu Pro configuration settings

      positional arguments:
        key_value_pair  key=value pair to configure for Ubuntu Pro services. Key
                        must be one of: http_proxy, https_proxy, apt_http_proxy,
                        apt_https_proxy, ua_apt_http_proxy, ua_apt_https_proxy,
                        global_apt_http_proxy, global_apt_https_proxy,
                        update_messaging_timer, metering_timer, apt_news,
                        apt_news_url

      (optional arguments|options):
        -h, --help      show this help message and exit
      """
    When I run `pro config unset --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro config unset \[-h\] key

      Unset Ubuntu Pro configuration setting

      positional arguments:
        key         configuration key to unset from Ubuntu Pro services. One of:
                    http_proxy, https_proxy, apt_http_proxy, apt_https_proxy,
                    ua_apt_http_proxy, ua_apt_https_proxy, global_apt_http_proxy,
                    global_apt_https_proxy, update_messaging_timer, metering_timer,
                    apt_news, apt_news_url

      (optional arguments|options):
        -h, --help  show this help message and exit
      """

    Examples: ubuntu release
      | release | machine_type  |
      | xenial  | lxd-container |
      | bionic  | lxd-container |
      | focal   | lxd-container |
      | jammy   | lxd-container |
      | noble   | lxd-container |

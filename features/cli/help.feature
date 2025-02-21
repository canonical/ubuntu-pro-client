Feature: Pro Client help text

  @arm64
  Scenario Outline: Help text for the Pro Client commands
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro [-h] [--debug] [--version] <command> ...

      Quick start commands:

        status           current status of all Ubuntu Pro services
        attach           attach this machine to an Ubuntu Pro subscription
        enable           enable a specific Ubuntu Pro service on this machine
        system           show system information related to Pro services
        security-status  list available security updates for the system

      Security-related commands:

        cve              show information about a CVE
        cves             list the vulnerabilities that affect the system
        fix              check for and mitigate the impact of a CVE/USN on this system

      Troubleshooting-related commands:

        collect-logs     collect Pro logs and debug information

      Other commands:

        api              Calls the Client API endpoints.
        auto-attach      automatically attach on supported platforms
        config           manage Ubuntu Pro configuration on this machine
        detach           remove this machine from an Ubuntu Pro subscription
        disable          disable a specific Ubuntu Pro service on this machine
        refresh          refresh Ubuntu Pro services

      Flags:

        -h, --help       Displays help on pro and command line options
        --debug          show all debug log messages to console
        --version        show version of pro

      Use pro <command> --help for more information about a command.
      """
    # '--help' and 'help' should both work and produce the same output
    When I run `pro help` as non-root
    Then I will see the following on stdout
      """
      usage: pro [-h] [--debug] [--version] <command> ...

      Quick start commands:

        status           current status of all Ubuntu Pro services
        attach           attach this machine to an Ubuntu Pro subscription
        enable           enable a specific Ubuntu Pro service on this machine
        system           show system information related to Pro services
        security-status  list available security updates for the system

      Security-related commands:

        cve              show information about a CVE
        cves             list the vulnerabilities that affect the system
        fix              check for and mitigate the impact of a CVE/USN on this system

      Troubleshooting-related commands:

        collect-logs     collect Pro logs and debug information

      Other commands:

        api              Calls the Client API endpoints.
        auto-attach      automatically attach on supported platforms
        config           manage Ubuntu Pro configuration on this machine
        detach           remove this machine from an Ubuntu Pro subscription
        disable          disable a specific Ubuntu Pro service on this machine
        refresh          refresh Ubuntu Pro services

      Flags:

        -h, --help       Displays help on pro and command line options
        --debug          show all debug log messages to console
        --version        show version of pro

      Use pro <command> --help for more information about a command.
      """
    When I run `pro collect-logs --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro collect-logs [-h] [-o OUTPUT]

      Collect logs and relevant system information into a tarball.
      This information can be later used for triaging/debugging issues.

      <options_string>:
        -h, --help            show this help message and exit
        -o OUTPUT, --output OUTPUT
                              tarball where the logs will be stored. (Defaults to
                              ./pro_logs.tar.gz)
      """
    When I run `pro api --help` as non-root
    Then stdout matches regexp:
      """
      usage: pro api \[-h\] \[--show-progress\] \[--args \[OPTIONS .*\]\](.|\n)*\[--data DATA\](.|\n)*
                     endpoint

      Calls the Client API endpoints.

      For a list of all of the supported endpoints and their structure,
      please refer to the Pro Client API reference guide:

      https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/references/api/

      positional arguments:
        endpoint              API endpoint to call

      <options_string>:
        -h, --help            show this help message and exit
        --show-progress       For endpoints that support progress updates, show each(.|\n)*
                              progress update on a new line in JSON format
        --args \[OPTIONS .*\](.|\n)*Options to pass to the API endpoint, formatted as(.|\n)*
                              key=value
        --data DATA           arguments in JSON format to the API endpoint
      """
    When I run `pro disable --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro disable [-h] [--assume-yes] [--format {cli,json}] [--purge]
                         service [service ...]

      Disable one or more Ubuntu Pro services.

      positional arguments:
        service              the name(s) of the Ubuntu Pro services to disable. One
                             of: anbox-cloud, cc-eal, cis, esm-apps, esm-infra,
                             fips, fips-preview, fips-updates, landscape, livepatch,
                             realtime-kernel, ros, ros-updates

      <options_string>:
        -h, --help           show this help message and exit
        --assume-yes         do not prompt for confirmation before performing the
                             disable
        --format {cli,json}  output in the specified format (default: cli)
        --purge              disable the service and remove/downgrade related
                             packages (experimental)
      """
    When I run `pro enable --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro enable [-h] [--assume-yes] [--access-only] [--beta]
                        [--format {cli,json}] [--variant VARIANT]
                        service [service ...]

      Activate and configure this machine's access to one or more Ubuntu Pro
      services.

      positional arguments:
        service              the name(s) of the Ubuntu Pro services to enable. One
                             of: anbox-cloud, cc-eal, cis, esm-apps, esm-infra,
                             fips, fips-preview, fips-updates, landscape, livepatch,
                             realtime-kernel, ros, ros-updates

      <options_string>:
        -h, --help           show this help message and exit
        --assume-yes         do not prompt for confirmation before performing the
                             enable
        --access-only        do not auto-install packages. Valid for cc-eal, cis and
                             realtime-kernel.
        --beta               allow beta service to be enabled
        --format {cli,json}  output in the specified format (default: cli)
        --variant VARIANT    The name of the variant to use when enabling the
                             service
      """
    When I run `pro attach --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro attach [-h] [--no-auto-enable] [--attach-config ATTACH_CONFIG]
                        [--format {cli,json}]
                        [token]

      Attach this machine to an Ubuntu Pro subscription with a token obtained from:
      https://ubuntu.com/pro/dashboard

      When running this command without a token, it will generate a short code
      and prompt you to attach the machine to your Ubuntu Pro account using
      a web browser.

      The "attach-config" option can be used to provide a file with the token
      and optionally, a list of services to enable after attaching. To know more,
      visit:
      https://canonical-ubuntu-pro-client.readthedocs-hosted.com/en/latest/howtoguides/how_to_attach_with_config_file/

      The exit code will be:

          * 0: on successful attach
          * 1: in case of any error while trying to attach
          * 2: if the machine is already attached

      positional arguments:
        token                 token obtained for Ubuntu Pro authentication

      <options_string>:
        -h, --help            show this help message and exit
        --no-auto-enable      do not enable any recommended services automatically
        --attach-config ATTACH_CONFIG
                              use the provided attach config file instead of passing
                              the token on the cli
        --format {cli,json}   output in the specified format (default: cli)
      """
    When I run `pro auto-attach --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro auto-attach [-h]

      Automatically attach on an Ubuntu Pro cloud instance.

      <options_string>:
        -h, --help  show this help message and exit
      """
    When I run `pro detach --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro detach [-h] [--assume-yes] [--format {cli,json}]

      Detach this machine from an Ubuntu Pro subscription.

      <options_string>:
        -h, --help           show this help message and exit
        --assume-yes         do not prompt for confirmation before performing the
                             detach
        --format {cli,json}  output in the specified format (default: cli)
      """
    When I run `pro security-status --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro security-status [-h] [--format {json,yaml,text}]
                                 [--thirdparty | --unavailable | --esm-infra | --esm-apps]

      Show security updates for packages in the system, including all
      available Expanded Security Maintenance (ESM) related content.

      Shows counts of how many packages are supported for security updates
      in the system.

      If the format is set to JSON or YAML it shows a summary of the
      installed packages based on the origin:

          - main/restricted/universe/multiverse: Packages from the Ubuntu archive.
          - esm-infra/esm-apps: Packages from the ESM archive.
          - third-party: Packages installed from non-Ubuntu sources.
          - unknown: Packages which don't have an installation source (like local
            deb packages or packages for which the source was removed).

      The output contains basic information about Ubuntu Pro. For a
      complete status on Ubuntu Pro services, run 'pro status'.

      <options_string>:
        -h, --help            show this help message and exit
        --format {json,yaml,text}
                              output in the specified format (default: text)
        --thirdparty          List and present information about third-party
                              packages
        --unavailable         List and present information about unavailable
                              packages
        --esm-infra           List and present information about esm-infra packages
        --esm-apps            List and present information about esm-apps packages
      """
    When I run `pro fix --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro fix [-h] [--dry-run] [--no-related] security_issue

      Inspect and resolve Common Vulnerabilities and Exposures (CVEs) and
      Ubuntu Security Notices (USNs) on this machine.

      The exit code will be:

          * 0: the fix was successfully applied or the system is not affected
          * 1: the fix cannot be applied
          * 2: the fix was applied but requires a reboot before it takes effect

      positional arguments:
        security_issue  Security vulnerability ID to inspect and resolve on this
                        system. Format: CVE-yyyy-nnnn, CVE-yyyy-nnnnnnn or USN-nnnn-
                        dd

      <options_string>:
        -h, --help      show this help message and exit
        --dry-run       If used, fix will not actually run but will display
                        everything that will happen on the machine during the
                        command.
        --no-related    If used, when fixing a USN, the command will not try to also
                        fix related USNs to the target USN.
      """
    When I run `pro status --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro status [-h] [--wait] [--format {tabular,json,yaml}]
                        [--simulate-with-token TOKEN] [--all]

      Report current status of Ubuntu Pro services on system.

      This shows whether this machine is attached to an Ubuntu Pro
      support contract. When attached, the report includes the specific
      support contract details including contract name, expiry dates, and the
      status of each service on this system.

      The attached status output has four columns:

          * SERVICE: Name of the service.
          * ENTITLED: Whether the contract to which this machine is attached
            entitles use of this service. Possible values are: yes or no.
          * STATUS: Whether the service is enabled on this machine. Possible
            values are: enabled, disabled, n/a (if your contract entitles
            you to the service, but it isn't available for this machine) or - (if
            you aren't entitled to this service).
          * DESCRIPTION: A brief description of the service.

      The unattached status output instead has three columns. SERVICE
      and DESCRIPTION are the same as above, and there is the addition
      of:

          * AVAILABLE: Whether this service would be available if this machine
            were attached. The possible values are yes or no.

      If "simulate-with-token" is used, then the output has five
      columns. SERVICE, AVAILABLE, ENTITLED and DESCRIPTION are the same
      as mentioned above, and AUTO_ENABLED shows whether the service is set
      to be enabled when that token is attached.

      If the "all" flag is set, beta and unavailable services are also
      listed in the output.

      <options_string>:
        -h, --help            show this help message and exit
        --wait                Block waiting on pro to complete
        --format {tabular,json,yaml}
                              output in the specified format (default: tabular)
        --simulate-with-token TOKEN
                              simulate the output status using a provided token
        --all                 Include unavailable and beta services
      """
    When I run `pro refresh --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro refresh [-h] [{contract,config,messages}]

      Refresh three distinct Ubuntu Pro related artifacts in the system:

          * contract: Update contract details from the server.
          * config:   Reload the config file.
          * messages: Update APT and MOTD messages related to Pro.

      You can individually target any of the three specific actions,
      by passing the target name to the command. If no target
      is specified, all targets are refreshed.

      positional arguments:
        {contract,config,messages}
                              Target to refresh.

      <options_string>:
        -h, --help            show this help message and exit
      """
    When I run `pro system --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro system [-h] {reboot-required} ...

      Outputs system-related information about Pro services.

      <options_string>:
        -h, --help         show this help message and exit

      Available Commands:
        {reboot-required}
          reboot-required  does the system need to be rebooted
      """
    When I run `pro system reboot-required --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro system reboot-required [-h]

      Report the current reboot-required status for the machine.

      This command will output one of the three following states
      for the machine regarding reboot:

          * no: The machine doesn't require a reboot.
          * yes: The machine requires a reboot.
          * yes-kernel-livepatches-applied: There are only kernel-related
            packages that require a reboot, but Livepatch has already provided
            patches for the current running kernel. The machine still needs a
            reboot, but you can assess if the reboot can be performed in the
            nearest maintenance window.

      <options_string>:
        -h, --help  show this help message and exit
      """
    When I run `pro config --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro config [-h] {show,set,unset} ...

      Manage Ubuntu Pro Client configuration on this machine.

      <options_string>:
        -h, --help        show this help message and exit

      Available Commands:
        {show,set,unset}
          show            Show customizable configuration settings.
          set             Set and apply Ubuntu Pro configuration settings.
          unset           Unset an Ubuntu Pro configuration setting, restoring the
                          default value.
      """
    When I run `pro config show --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro config show [-h] [key]

      Show customizable configuration settings.

      positional arguments:
        key         Optional key or key(s) to show configuration settings.

      <options_string>:
        -h, --help  show this help message and exit
      """
    When I run `pro config set --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro config set [-h] key_value_pair

      Set and apply Ubuntu Pro configuration settings.

      positional arguments:
        key_value_pair  key=value pair to configure for Ubuntu Pro services. Key
                        must be one of: http_proxy, https_proxy, apt_http_proxy,
                        apt_https_proxy, ua_apt_http_proxy, ua_apt_https_proxy,
                        global_apt_http_proxy, global_apt_https_proxy,
                        update_messaging_timer, metering_timer, apt_news,
                        apt_news_url, vulnerability_data_url_prefix,
                        lxd_guest_attach

      <options_string>:
        -h, --help      show this help message and exit
      """
    When I run `pro config unset --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro config unset [-h] key

      Unset an Ubuntu Pro configuration setting, restoring the default value.

      positional arguments:
        key         configuration key to unset from Ubuntu Pro services. One of:
                    http_proxy, https_proxy, apt_http_proxy, apt_https_proxy,
                    ua_apt_http_proxy, ua_apt_https_proxy, global_apt_http_proxy,
                    global_apt_https_proxy, update_messaging_timer, metering_timer,
                    apt_news, apt_news_url, vulnerability_data_url_prefix,
                    lxd_guest_attach

      <options_string>:
        -h, --help  show this help message and exit
      """
    When I run `pro cves --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro cves [-h] [--unfixable] [--fixable]

      List the CVE vulnerabilities that affects the system.

      <options_string>:
        -h, --help   show this help message and exit
        --unfixable  List only vulnerabilities without a fix available
        --fixable    List only vulnerabilities with a fix available
      """
    When I run `pro cve --help` as non-root
    Then I will see the following on stdout
      """
      usage: pro cve [-h] cve

      Show all available information about a given CVE.

      positional arguments:
        cve         CVE to display information. Format: CVE-yyyy-nnnn or CVE-yyyy-
                    nnnnnnn

      <options_string>:
        -h, --help  show this help message and exit
      """

    Examples: ubuntu release
      | release | machine_type  | options_string     |
      | xenial  | lxd-container | optional arguments |
      | bionic  | lxd-container | optional arguments |
      | focal   | lxd-container | optional arguments |
      | jammy   | lxd-container | options            |
      | noble   | lxd-container | options            |

  Scenario Outline: Help command on an attached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I attach `contract_token` with sudo
    And I run `pro help esm-infra` with sudo
    Then I will see the following on stdout:
      """
      Name:
      esm-infra

      Entitled:
      yes

      Status:
      <infra-status>

      Help:
      Expanded Security Maintenance for Infrastructure provides access to a private
      PPA which includes available high and critical CVE fixes for Ubuntu LTS
      packages in the Ubuntu Main repository between the end of the standard Ubuntu
      LTS security maintenance and its end of life. It is enabled by default with
      Ubuntu Pro. You can find out more about the service at
      https://ubuntu.com/security/esm
      """
    When I run `pro help esm-infra --format json` with sudo
    Then API full output matches regexp:
      """
      {
        "name": "esm-infra",
        "entitled": "yes",
        "status": "enabled",
        "help": "Expanded Security Maintenance for Infrastructure provides access to a private\nPPA which includes available high and critical CVE fixes for Ubuntu LTS\npackages in the Ubuntu Main repository between the end of the standard Ubuntu\nLTS security maintenance and its end of life. It is enabled by default with\nUbuntu Pro. You can find out more about the service at\nhttps://ubuntu.com/security/esm"
      }
      """
    And I verify that running `pro help invalid-service` `with sudo` exits `1`
    And I will see the following on stderr:
      """
      No help available for 'invalid-service'
      """

    Examples: ubuntu release
      | release  | machine_type  | infra-status |
      | bionic   | lxd-container | enabled      |
      | xenial   | lxd-container | enabled      |
      | focal    | lxd-container | enabled      |
      | jammy    | lxd-container | enabled      |
      | noble    | lxd-container | enabled      |
      | oracular | lxd-container | n/a          |

  @arm64
  Scenario Outline: Help command on an unattached machine
    Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
    When I run `pro help esm-infra` as non-root
    Then I will see the following on stdout:
      """
      Name:
      esm-infra

      Available:
      <infra-available>

      Help:
      Expanded Security Maintenance for Infrastructure provides access to a private
      PPA which includes available high and critical CVE fixes for Ubuntu LTS
      packages in the Ubuntu Main repository between the end of the standard Ubuntu
      LTS security maintenance and its end of life. It is enabled by default with
      Ubuntu Pro. You can find out more about the service at
      https://ubuntu.com/security/esm
      """
    When I run `pro help esm-infra --format json` with sudo
    Then I will see the following on stdout:
      """
      {"name": "esm-infra", "available": "<infra-available>", "help": "Expanded Security Maintenance for Infrastructure provides access to a private\nPPA which includes available high and critical CVE fixes for Ubuntu LTS\npackages in the Ubuntu Main repository between the end of the standard Ubuntu\nLTS security maintenance and its end of life. It is enabled by default with\nUbuntu Pro. You can find out more about the service at\nhttps://ubuntu.com/security/esm"}
      """
    When I verify that running `pro help invalid-service` `with sudo` exits `1`
    Then I will see the following on stderr:
      """
      No help available for 'invalid-service'
      """
    When I verify that running `pro --no-command` `with sudo` exits `2`
    Then I will see the following on stderr:
      """
      usage: pro [-h] [--debug] [--version] <command> ...
      pro: error: the following arguments are required: <command>
      """

    Examples: ubuntu release
      | release  | machine_type  | infra-available |
      | xenial   | lxd-container | yes             |
      | bionic   | lxd-container | yes             |
      | bionic   | wsl           | yes             |
      | focal    | lxd-container | yes             |
      | focal    | wsl           | yes             |
      | jammy    | lxd-container | yes             |
      | jammy    | wsl           | yes             |
      | noble    | lxd-container | yes             |
      | oracular | lxd-container | no              |

Feature: Full Auto-Attach Endpoint

    @series.lts
    @uses.config.machine_type.aws.pro
    @uses.config.machine_type.azure.pro
    @uses.config.machine_type.gcp.pro
    Scenario Outline: Run auto-attach on cloud instance.
        Given a `<release>` machine with ubuntu-advantage-tools installed
        When I create the file `/etc/ubuntu-advantage/uaclient.conf` with the following:
        """
        contract_url: 'https://contracts.canonical.com'
        data_dir: /var/lib/ubuntu-advantage
        log_level: debug
        log_file: /var/log/ubuntu-advantage.log
        """
        When I create the file `/tmp/full_auto_attach.py` with the following:
        """
        from uaclient.api.u.pro.attach.auto.full_auto_attach.v1 import full_auto_attach, FullAutoAttachOptions

        full_auto_attach(FullAutoAttachOptions(enable=["esm-infra", "esm-apps"]))
        """
        And I run `python3 /tmp/full_auto_attach.py` with sudo
        And I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        esm-apps      +yes +enabled +Expanded Security Maintenance for Applications
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        """
        Then stdout matches regexp:
        """
        livepatch     +yes +disabled  +Canonical Livepatch service
        """
        Examples:
           | release |
           | xenial  |
           | bionic  |
           | focal   |
           | jammy   |
           

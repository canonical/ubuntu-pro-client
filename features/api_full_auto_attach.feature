Feature: Full Auto-Attach Endpoint

    Scenario Outline: Run auto-attach on cloud instance.
        Given a `<release>` `<machine_type>` machine with ubuntu-advantage-tools installed
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

        full_auto_attach(FullAutoAttachOptions(enable=["esm-infra"]))
        """
        And I run `python3 /tmp/full_auto_attach.py` with sudo
        And I run `pro status --all` with sudo
        Then stdout matches regexp:
        """
        esm-infra     +yes +enabled +Expanded Security Maintenance for Infrastructure
        """
        Then stdout matches regexp:
        """
        livepatch     +yes +(disabled|n/a)  +(Canonical Livepatch service|Current kernel is not supported)
        """
        Examples:
           | release | machine_type |
           | xenial  | aws.pro      |
           | xenial  | azure.pro    |
           | xenial  | gcp.pro      |
           | bionic  | aws.pro      |
           | bionic  | azure.pro    |
           | bionic  | gcp.pro      |
           | focal   | aws.pro      |
           | focal   | azure.pro    |
           | focal   | gcp.pro      |
           | jammy   | aws.pro      |
           | jammy   | azure.pro    |
           | jammy   | gcp.pro      |
           

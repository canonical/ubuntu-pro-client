Feature: Command behaviour when unattached

    Scenario: Unattached detach in a trusty lxd container
        Given a trusty lxd container
          And ubuntu-advantage-tools is installed
        When I run `ua detach` as non-root
        Then I will see the following on stderr:
            """
            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """

    Scenario: Unattached refresh in a trusty lxd container
        Given a trusty lxd container
          And ubuntu-advantage-tools is installed
        When I run `ua refresh` as non-root
        Then I will see the following on stderr:
            """
            This machine is not attached to a UA subscription.
            See https://ubuntu.com/advantage
            """

    Scenario: Unattached enable in a trusty lxd container
        Given a trusty lxd container
          And ubuntu-advantage-tools is installed
        When I run `ua enable livepatch` as non-root
        Then I will see the following on stderr:
            """
            To use 'livepatch' you need an Ubuntu Advantage subscription.
            Personal and community subscriptions are available at no charge
            See https://ubuntu.com/advantage
            """

    Scenario: Unattached disable in a trusty lxd container
        Given a trusty lxd container
          And ubuntu-advantage-tools is installed
        When I run `ua disable livepatch` as non-root
        Then I will see the following on stderr:
            """
            To use 'livepatch' you need an Ubuntu Advantage subscription.
            Personal and community subscriptions are available at no charge
            See https://ubuntu.com/advantage
            """

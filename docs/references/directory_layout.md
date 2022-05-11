# Directory layout

The following describes the intent of UA client related directories:

| File/Directory | Intent |
| -------- | -------- |
| ./tools | Helpful scripts used to publish, release or test various aspects of UA client |
| ./features/ | Behave BDD integration tests for UA Client
| ./uaclient/ | collection of python modules which will be packaged into ubuntu-advantage-tools package to deliver the UA Client CLI |
| uaclient.entitlements | Service-specific \*Entitlement class definitions which perform enable, disable, status, and entitlement operations etc. All classes derive from base.py:UAEntitlement and many derive from repo.py:RepoEntitlement |
| ./uaclient/cli.py | The entry-point for the command-line client
| ./uaclient/clouds/ | Cloud-platform detection logic used in Ubuntu Pro to determine if a given should be auto-attached to a contract |
| uaclient.contract | Module for interacting with the Contract Server API |
| uaclient.messages | Module that contains the messages delivered by UA to the user |
| uaclient.security | Module that hold the logic used to run `ua fix` commands |
| ./apt-hook/ | the C++ apt-hook delivering MOTD and apt command notifications about UA support services |
| ./apt-conf.d/ | apt config files delivered to /etc/apt/apt-conf.d to automatically allow unattended upgrades of ESM security-related components. If apt proxy settings are configured, an additional apt config file will be placed here to configure the apt proxy. |
| /etc/ubuntu-advantage/uaclient.conf | Configuration file for the UA client.|
| /var/lib/ubuntu-advantage/private | `root` read-only directory containing Contract API responses, machine-tokens and service credentials |
| /var/log/ubuntu-advantage.log | `root` read-only log of ubuntu-advantage operations |

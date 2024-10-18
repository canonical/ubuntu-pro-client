# Directory layout

The following describes the intent of Ubuntu Pro Client related directories:

| File/Directory | Intent |
| -------- | -------- |
| ./tools | Helpful scripts used to publish, release or test various aspects of Ubuntu Pro Client |
| ./features/ | Behave BDD integration tests for Ubuntu Pro Client
| ./uaclient/ | collection of python modules which will be packaged into ubuntu-advantage-tools package to deliver the Ubuntu Pro Client CLI |
| uaclient.entitlements | Service-specific \*Entitlement class definitions which perform enable, disable, status, and entitlement operations etc. All classes derive from base.py:UAEntitlement and many derive from repo.py:RepoEntitlement |
| ./uaclient/cli.py | The entry-point for the command-line client
| ./uaclient/clouds/ | Cloud-platform detection logic used in Ubuntu Pro to determine if a given instance should be auto-attached to a contract |
| uaclient.contract | Module for interacting with the Contract Server API |
| uaclient.messages | Module that contains the messages delivered by `pro` to the user |
| uaclient.security | Module that hold the logic used to run `pro fix` commands |
| ./apt-hook/ | the C++ apt-hook delivering MOTD and apt command notifications about Ubuntu Pro support services |
| /etc/ubuntu-advantage/uaclient.conf | Configuration file for the Ubuntu Pro Client.|
| /var/lib/ubuntu-advantage/private | `root` read-only directory containing Contract API responses, machine-tokens and service credentials |
| /var/lib/ubuntu-advantage/machine-token.json | `world` readable file containing redacted Contract API responses, machine-tokens and service credentials |
| /var/log/ubuntu-advantage.log | `root` read-only log of ubuntu-advantage operations |

## Note

We have two `machine-token.json` files, located at:

- /var/lib/ubuntu-advantage/private/machine-token.json
- /var/lib/ubuntu-advantage/machine-token.json

The first file, located in the `private` directory, is root read-only. We have another world readable file in the `/var/lib/ubuntu-advantage` directory.

The latter is currently being used when calling the `pro status` command as a non-root user. This file is redacted to remove any sensitive user data.

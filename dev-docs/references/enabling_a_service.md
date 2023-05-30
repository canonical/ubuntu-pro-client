# Enabling a service

Each service controlled by Ubuntu Pro Client will have a python module in
uaclient/entitlements/\*.py which handles setup and teardown of services when
enabled or disabled.

If a contract entitles a machine to a service, `root` user can enable the
service with `pro enable <service>`.  If a service can be disabled
`pro disable <service>` will be permitted.

The goal of the Ubuntu Pro Client is to remain simple and flexible and let the
contracts backend drive dynamic changes in contract offerings and constraints.
In pursuit of that goal, the Ubuntu Pro Client obtains most of it's service constraints
from a machine token that it obtains from the Contract Server API.

The Ubuntu Pro Client is simple in that it relies on the machine token on the attached
machine to describe whether a service is applicable for an environment and what
configuration is required to properly enable that service.

Any interactions with the Contract Server API are defined as UAContractClient
class methods in [uaclient/contract.py](../../uaclient/contract.py).

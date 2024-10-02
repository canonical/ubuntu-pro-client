.. _architecture:

Architecture
************

Ubuntu Pro Client is a ``python3``-based command line utility. It provides a
CLI to attach, detach, enable, disable and check the status of support-related
services.

The package ``ubuntu-pro-client`` also provides a C++ APT hook which helps to
advertise ESM services, available packages in MOTD, and during various ``apt``
commands.

The ``ubuntu-pro-auto-attach`` package delivers auto-attach functionality via a
systemd service for various cloud platforms.

By default, Ubuntu machines are deployed in an "unattached" state. A machine
can be manually or automatically attached to a specific contract by interacting
with the Contract Server REST API. Any change in the state of services, or
machine attach, results in additional interactions with the Contract Server API
to validate such operations.

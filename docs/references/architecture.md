# Architecture

Ubuntu Advantage client, hereafter "UA client", is a python3-based command line
utility. It provides a CLI to attach, detach, enable,
disable and check status of support related services.

The package `ubuntu-advantage-tools` also provides a C++ APT hook which helps
advertise ESM service and available packages in MOTD and during various apt
commands.

The `ubuntu-advantage-pro` package delivers auto-attach functionality via init
scripts and systemd services for various cloud platforms.

By default, Ubuntu machines are deployed in an unattached state. A machine can
get manually or automatically attached to a specific contract by interacting
with the Contract Server REST API. Any change in state of services or machine
attach results in additional interactions with the Contract Server API to
validate such operations.

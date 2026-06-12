# Set up Workshop for Ubuntu Pro Client

[Canonical Workshop](https://canonical-workshop.readthedocs-hosted.com/) is the
recommended way to get a development environment running quickly. It manages a
sandboxed Ubuntu container with all required tooling pre-installed.

## Prerequisites

Workshop uses [LXD](https://documentation.ubuntu.com/lxd/default/tutorial/first_steps/) to manage containers. Install it before proceeding:

```bash
sudo snap install --channel 6/stable lxd
```

## Install Workshop

Use the latest installation instructions from [workshop](https://github.com/canonical/workshop).

## Clone the repository

```bash
git clone https://github.com/canonical/ubuntu-pro-client.git
cd ubuntu-pro-client
```

## Launch the workshop

From the root of the repository, run:

```bash
workshop launch
```

This builds a fresh Ubuntu 24.04 VM, installs the `uv` SDK, and mounts your
local checkout inside it. This may take a few minutes the first time.

## Verify the setup

Run the unit tests to confirm everything is working:

```bash
workshop test
```

If the tests pass, your environment is set up correctly.

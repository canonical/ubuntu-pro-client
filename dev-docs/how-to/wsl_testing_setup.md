# How to run the integration tests on WSL

The WSL integration tests run inside Ubuntu distributions on a Windows 11 host
in Azure. The behave harness reaches that host over SSH, creates a fresh WSL
distribution for each scenario, and runs the scenario inside it.

`tools/wsl-host/` is a Terraform module that creates a ready-to-use host and
destroys it again. The tests only need the host's IP address and the SSH key
that Terraform generates.

## Prerequisites

* [Terraform](https://developer.hashicorp.com/terraform/install) 1.5 or newer.
* Azure credentials, in either form the Azure providers accept:
  * `az login` with the Azure CLI, or
  * `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID` and
    `ARM_SUBSCRIPTION_ID` in the environment. These are the same values the
    `[azure]` section of `~/.config/pycloudlib.toml` holds as `client_id`,
    `client_secret`, `tenant_id` and `subscription_id`.
* `~/.config/pycloudlib.toml` with the `[azure]` section filled in. The behave
  harness uses it to start the host before a run and stop it afterwards.

## Create the host

```shell
terraform -chdir=tools/wsl-host init
terraform -chdir=tools/wsl-host apply
```

`apply` returns once the host is ready, which takes 10–15 minutes. It creates
a resource group named `wsl-test-rg` containing a Windows 11 Pro VM named
`wsl-test`, runs `bootstrap.ps1` on it (OpenSSH Server, WSL features, WSL,
winget, automatic logon), reboots it, and then waits until a post-logon task
has confirmed that winget and WSL work.

An SSH key pair is written to `tools/wsl-host/.ssh/`.

Variables are documented in `tools/wsl-host/variables.tf` and can be set with
`-var` or `TF_VAR_*`. For example, to install a WSL pre-release:

```shell
terraform -chdir=tools/wsl-host apply -var wsl_msi_url=prerelease
```

`latest` and `prerelease` are resolved when `bootstrap.ps1` runs, so two hosts
created at different times can get different WSL versions. Pass a direct
`.msi` URL to pin one.

## Run the tests

Export the connection details the harness expects, then run behave with
`machine_types=wsl`:

```shell
eval "$(terraform -chdir=tools/wsl-host output -raw behave_env)"
tox -e behave -- -D machine_types=wsl -D releases=jammy
```

`behave_env` sets `UACLIENT_BEHAVE_WSL_IP_ADDRESS`,
`UACLIENT_BEHAVE_WSL_PRIVKEY_PATH` and `UACLIENT_BEHAVE_WSL_PUBKEY_PATH`.

## Destroy the host

When you are finished testing, destroy the resources:

```shell
terraform -chdir=tools/wsl-host destroy
```

This removes the whole resource group and the local SSH key pair.

## Troubleshooting

`terraform -chdir=tools/wsl-host output -raw ssh_command` prints a command
that opens a shell on the Windows host. Bootstrap output is in
`C:\wsl-host\bootstrap.log` (before the reboot, runs as SYSTEM) and
`C:\wsl-host\phase2.log` (after automatic logon, runs as `ubuntu`). The host
is ready when `C:\wsl-host\READY` exists.

If `apply` fails in `bootstrap` or `wait-ready`, the error includes the
script's exit code and message. Fix the cause and run `apply` again; Terraform
re-runs only the failed step and everything after it.

The admin password, needed only for RDP or Bastion, is available with
`terraform -chdir=tools/wsl-host output -raw admin_password`.

The VM uses the *Standard* security type because Trusted Launch does not
support the nested virtualization WSL 2 requires, and `Windows_Client`
licensing because Windows 11 on Azure needs multitenant hosting rights. Both
are set in `tools/wsl-host/main.tf`.

## TODOs

There are post-provisioning steps specifically related to enabling `winget`.
Once all WSL distros that we support are "native" WSL distros, we can remove
the need for winget and can drop these post-provisioning steps.

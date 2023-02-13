# Get started with `pro` in airgapped environment
Want to use `pro` in an offline (=airgapped/internetless) environment? This how-to guide will help you understand how to use the power of Ubuntu Pro in an internetless environment.

We will show you how to use your existing token in the machine without Internet access and get the same resources as if your machine had network access.

What you’ll learn
* How to use the airgapped functionality
* How to configure the Pro client to use airgapped
* How to configure resources in the internetless environment

What you’ll need
* Preliminary Ubuntu Pro knowledge (refer [here](https://canonical-ubuntu-pro-client.readthedocs-hosted.com/) for more info)
* Two Ubuntu machines (one in the airgapped & one in the non-airgapped environment) running 16.04 LTS, 18.04 LTS, 20.04 LTS or 22.04 LTS
* `sudo` access on both machines
* Existing Ubuntu One account
* Ubuntu Pro client version 27.11.2 or newer on the airgapped machine

## Before we start
1. Check your machines are up-to-date: \
`sudo apt update && sudo apt upgrade`
2. Check the Ubuntu Pro client is installed on the airgapped machine: \
`pro --version`
3. Get the token from the [Ubuntu Pro dashboard](https://ubuntu.com/pro/dashboard) you plan to use in the airgapped environment. In this guide, we’ll refer to this token as `[YOUR_CONTRACT_TOKEN]`


## Installation
Run these commands on both machines:
```bash
sudo add-apt-repository ppa:yellow/ua-airgapped && sudo apt update
sudo apt install ua-airgapped contracts-airgapped get-resource-tokens
```

These three commands serve the following purposes:
1. `ua-airgapped` creates the configuration for running the server locally
2. `contracts-airgapped` runs the server for the Ubuntu Pro client
3. `get-resource-tokens` fetches resource tokens for setting up mirrors of Canonical repositories (as we cannot access Canonical-hosted resources in an offline environment)


## Get configuration to set up mirrors
The Ubuntu Pro client cannot access Canonical-hosted services in an offline environment, so we will mirror these repositories locally.

First, find out the repositories’ URLs of all the resources your contract is entitled to. Run the following in a non-airgapped environment: \
`echo '[YOUR_CONTRACT_TOKEN]:' | ua-airgapped | grep 'aptURL:'`

Then, get the resource tokens to access these resources in a non-airgapped environment: \
`get-resource-tokens [YOUR_CONTRACT_TOKEN]`

Stdout from `get-resource-tokens` gives pairs of services and their resource tokens (one token per service). The repository URL is specified as `aptURL` from the first command and, together with the resource token, they are required to set up a mirror, be it `apt-mirror`, `aptly`, Landscape or another software.

You can check the resource token's correctness. For example, let’s say we want to set a mirror for `esm-infra`. It has `aptURL: https://esm.ubuntu.com`. If the resource token is `[ESM_INFRA_RESOURCE_TOKEN]`, then the command on the non-airgapped machine will be:
```bash
/usr/lib/apt/apt-helper download-file https://bearer:[ESM_INFRA_RESOURCE_TOKEN]@esm.ubuntu.com/ubuntu/ /tmp/check-esm-resource-token.txt
```
Response must be `200`. `401 Unauthorized` shows that the resource token or the URL is wrong. Please note that the specifics of setting up mirrors may be different depending on the product, but the bearer authentication will be identical in all cases, so refer to the command above to distinguish between airgapped and mirror problems.

## Set up mirrors
If you have experience in setting up mirrors, this section is optional for you. However, if you want to get started with the simplest option of setting up mirrors and have no prior experience, keep reading.

Suppose you want to set up mirrors for esm-infra. Then, the steps to set up a mirror would be:
1. Install `apt-mirror`: \
`sudo apt install apt-mirror`
2. Fetch the resource token for `esm-infra` (as per the section above).
3. Change the `/etc/apt/mirror.list` file to the following contents:
	```
	set nthreads     20
	set _tilde 0

	deb https://bearer:[ESM_INFRA_RESOURCE_TOKEN]@esm.ubuntu.com/infra/ubuntu/ jammy-infra-updates main
	deb https://bearer:[ESM_INFRA_RESOURCE_TOKEN]@esm.ubuntu.com/infra/ubuntu/ jammy-infra-security main

	clean http://archive.ubuntu.com/ubuntu
	```
4. Run `apt-mirror`: \
`sudo -u apt-mirror apt-mirror`
5. Serve the `esm-infra` mirror on port `9090` (will be `[ESM_INFRA_MIRROR_URL]` in the next section): \
`python3 -m http.server --directory /var/spool/apt-mirror/mirror/esm.ubuntu.com/infra/ 9090`


## Get configuration to run the server
The prerequisites for this step are:
1. Mirrors of needed resources are set up on the airgapped machine
2. Mirrors of needed resources are served on some port on the airgapped machine

We need to create such a configuration for our server so that it points to the local mirror server on the airgapped machine, not the Canonical one. For example, if we want to use `esm-infra` in the airgapped environment, create the `02-overridden.yml` file on the non-airgapped machine with the following contents:
```yaml
[YOUR_CONTRACT_TOKEN]:
  esm-infra:
    directives:
      aptURL: [ESM_INFRA_MIRROR_URL]
```
Run `ua-airgapped` for the new config in non-airgapped environment: `cat 02-overridden.yml | ua-airgapped > 02-server-ready.yml`

`02-server-ready.yml` is our final configuration to run the server.

## Running the server and final tweaks
Run the following commands in the airgapped environment:
1. Run the server: `contracts-airgapped --input=./02-server-ready.yml`
2. Change the `contract_url` setting in `uaclient.conf` to point to the server: `http://1.2.3.4:8484`. Here `1.2.3.4` is the IP address of the airgapped machine.
3. Run `sudo pro refresh` to check everything works fine.
4. Finally, attach your token: `sudo pro attach [YOUR_CONTRACT_TOKEN]`.

## Congratulations!
That’s been a long run, but you’ve made it! Now you are all set to run all the `pro` commands in the airgapped environment as you are used to.

# Create an Ubuntu FIPS Docker image

> Requires at least UA Client version 27.7

## Step 1: Acquire your Ubuntu Advantage (UA) token

Your UA token can be found on your Ubuntu Advantage dashboard. To access your dashboard, you need an [Ubuntu One](https://login.ubuntu.com/) account. If you purchased a UA subscription and don't yet have an Ubuntu One account, be sure to use the same email address used to purchase your subscription. If you haven't purchased a UA subscription, don't worry! You get a free token for personal use with your Ubuntu One account, no purchase necessary.

The Ubuntu One account functions as a Single Sign On, so once logged in we can go straight to the Ubuntu Advantage dashboard at [ubuntu.com/advantage](https://ubuntu.com/advantage). Then we should see a list of our subscriptions (including the free for personal use subscription) in the left-hand column. Click on the subscription that you wish to use for this tutorial if it is not already selected. On the right we will now see the details of our subscription including our secret token under the "Subscription" header next to the "🔗" symbol.

> **Note**
> The UA token should be kept secret. It is used to uniquely identify your Ubuntu Advantage subscription.

## Step 2: Create a UA Attach Config file

First create a directory for this tutorial.

```bash
mkdir ua_fips_tutorial
cd ua_fips_tutorial
```

Create a file named `ua-attach-config.yaml`.

```bash
touch ua-attach-config.yaml
```

Edit the file and add the following contents:

```yaml
token: YOUR_TOKEN
enable_services:
  - fips
```

Replace `YOUR_TOKEN` with the UA token we got from [ubuntu.com/advantage](https://ubuntu.com/advantage) in Step 1.

## Step 3: Create a Dockerfile

Create a file named `Dockerfile`.

```bash
touch Dockerfile
```

Edit the file and add the following contents:

```dockerfile
FROM ubuntu:focal

RUN --mount=type=secret,id=ua-attach-config \
    apt-get update \
    && apt-get install --no-install-recommends -y ubuntu-advantage-tools ca-certificates \
    && ua attach --attach-config /run/secrets/ua-attach-config \

    && apt-get upgrade -y \
    && apt-get install -y openssl libssl1.1 libssl1.1-hmac libgcrypt20 libgcrypt20-hmac strongswan strongswan-hmac openssh-client openssh-server \

    && apt-get purge --auto-remove -y ubuntu-advantage-tools ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

This Dockerfile will enable FIPS in the container, upgrade all packages and install the FIPS version of `openssl`. For more details on how this works, see [How to Enable UA Services in a Dockerfile](../howtoguides/enable_ua_in_dockerfile.md)

## Step 4: Build the Docker image

Build the docker image with the following command:

```bash
DOCKER_BUILDKIT=1 docker build . --secret id=ua-attach-config,src=ua-attach-config.yaml -t ubuntu-bionic-fips
```

This will pass the attach-config as a [BuildKit Secret](https://docs.docker.com/develop/develop-images/build_enhancements/#new-docker-build-secret-information) so that the finished docker image will not contain your UA token.

## Step 5: Test the Docker image

> **Warning**
> The docker image isn't considered fully FIPS compliant unless it is running on a host Ubuntu machine that is FIPS compliant.

Let's check to make sure the FIPS version of openssl is installed in the container.

```bash
docker run -it ubuntu-bionic-fips dpkg-query --show openssl
```
Should show something like `openssl 1.1.1-1ubuntu2.fips.2.1~18.04.6.2` (notice "fips" in the version name).

We can now use the build docker image's FIPS compliant `openssl` to connect to `https://ubuntu.com`.

```bash
docker run -it ubuntu-bionic-fips sh -c "echo | openssl s_client -connect ubuntu.com:443"
```

That should print information about the certificates of ubuntu.com and the algorithms used during the TLS handshake.


## Success

That's it! You could now push this image to a private registry and use it as the base of other docker images using `FROM`.

If you want to learn more about how the steps in this tutorial work, take a look at the more generic [How to Enable UA Services in a Dockerfile](../howtoguides/enable_ua_in_dockerfile.md).

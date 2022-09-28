# How to Enable Ubuntu Pro Services in a Dockerfile

> Requires at least Ubuntu Pro Client version 27.7

Ubuntu Pro comes with several services, some of which can be useful in docker. For example, Expanded Security Maintenance of packages and FIPS certified packages may be desirable in a docker image. In this how-to-guide, we show how you can use the `pro` tool to take advantage of these services in your Dockerfile.


## Step 1: Create an Ubuntu Pro Attach Config file

> **Note**
> The Ubuntu Pro Attach Config file will contain your Ubuntu Pro Contract token and should be treated as a secret file.

An attach config file for `pro` is a yaml file that specifies some options when running `pro attach`. The file has two fields, `token` and `enable_services` and looks something like this:

```yaml
token: TOKEN
enable_services:
  - service1
  - service2
  - service3
```

The `token` field is required and must be set to your Ubuntu Pro token that you can get from signing into [ubuntu.com/pro](https://ubuntu.com/pro).

The `enable_services` field value is a list of Ubuntu Pro service names. When it is set, then the services specified will be automatically enabled after attaching with your Ubuntu Pro token.

Service names that you may be interested in enabling in your docker builds include:
- `esm-infra`
- `esm-apps`
- `fips`
- `fips-updates`

You can find out more about these services by running `pro help service-name` on any Ubuntu machine.


## Step 2: Create a Dockerfile to use `pro` and your attach config file

Your Dockerfile is going to look something like this.

There are comments inline explaining each line.

```dockerfile
# Base off of the LTS of your choice
FROM ubuntu:focal

# We mount a BuildKit secret here to access the attach config file which should
# be kept separate from the Dockerfile and managed in a secure fashion since it
# needs to contain your Ubuntu Pro token.
# In the next step, we demonstrate how to pass the file as a secret when
# running docker build.
RUN --mount=type=secret,id=pro-attach-config \

    # First we update apt so we install the correct versions of packages in
    # the next step
    apt-get update \

    # Here we install `pro` (ubuntu-advantage-tools) as well as ca-certificates,
    # which is required to talk to the Ubuntu Pro authentication server securely.
    && apt-get install --no-install-recommends -y ubuntu-advantage-tools ca-certificates \

    # With pro installed, we attach using our attach config file from the
    # previous step
    && pro attach --attach-config /run/secrets/pro-attach-config \

    ###########################################################################
    # At this point, the container has access to all Ubuntu Pro services
    # specified in the attach config file.
    ###########################################################################

    # Always upgrade all packages to the latest available version with the Ubuntu Pro
    # services enabled.
    && apt-get upgrade -y \

    # Then, you can install any specific packages you need for your docker
    # container.
    # Install them here, while Ubuntu Pro is enabled, so that you get the appropriate
    # versions.
    # Any `apt-get install ...` commands you have in an existing Dockerfile
    # that you may be migrating to use Ubuntu Pro should probably be moved here.
    && apt-get install -y openssl \

    ###########################################################################
    # Now that we've upgraded and installed any packages from the Ubuntu Pro
    # services, we can clean up.
    ###########################################################################

    # This purges ubuntu-advantage-tools, including all Ubuntu Pro related
    # secrets from the system.
    ###########################################################################
    # IMPORTANT: As written here, this command assumes your container does not
    # need ca-certificates so it is purged as well.
    # If your container needs ca-certificates, then do not purge it from the
    # system here.
    ###########################################################################
    && apt-get purge --auto-remove -y ubuntu-advantage-tools ca-certificates \

    # Finally, we clean up the apt lists which shouldn't be needed anymore
    # because any `apt-get install`s should've happened above. Cleaning these
    # lists keeps your image smaller.
    && rm -rf /var/lib/apt/lists/*


# Now, with all of your ubuntu apt packages installed, including all those
# from Ubuntu Pro services, you can continue the rest of your app-specific Dockerfile.
```

An important point to note about the above Dockerfile is that all of the `apt` and `pro` commands happen inside of one Dockerfile `RUN` instruction. This is critical and must not be changed. Keeping everything as written inside of one `RUN` instruction has two key benefits:

1. Prevents any Ubuntu Pro Subscription-related tokens and secrets from being leaked in an image layer
2. Keeps the image as small as possible by cleaning up extra packages and files before the layer is finished.

> **Note**
> These benefits could also be attained by squashing the image.

## Step 3: Build the Docker image


Now, with our attach config file and Dockerfile created, we can build the image with a command like the following

```bash
DOCKER_BUILDKIT=1 docker build . --secret id=pro-attach-config,src=pro-attach-config.yaml -t ubuntu-focal-pro
```

There are two important pieces of this command.

1. We enable BuildKit with `DOCKER_BUILDKIT=1`. This is necessary to support the secret mount feature.
2. We use the secret mount feature of BuildKit with `--secret id=pro-attach-config,src=pro-attach-config.yaml`. This is what passes our attach config file in to be securely used by the `RUN --mount=type=secret,id=pro-attach-config` command in the Dockerfile.

## Success

Congratulations! At this point, you should have a docker image that has been built with Ubuntu Pro packages installed from whichever Ubuntu Pro service you required.

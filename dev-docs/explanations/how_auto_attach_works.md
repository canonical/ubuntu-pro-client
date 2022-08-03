# How auto-attach works

The `pro auto-attach` command follows a specific flow on every **Ubuntu Pro** image:

1. Identify which cloud the command is running on. This is achieved by running
   the `cloud-id` command provided by the [cloud-init](https://cloudinit.readthedocs.io/en/latest/)
   package. Currently, we only support the following clouds when
   running the command: AWS, Azure and GCP. The command will fail if performed on other
   cloud types.

2. Fetch the cloud metadata. This metadata is a cryptographically signed json blob
   that provides the necessary information for the contract server to validate
   the machine and return a valid pro token. To fetch that metadata, every cloud
   provide a different endpoint to reach it:

   * **AWS**: http://169.254.169.254/latest/dynamic/instance-identity/pkcs7
   * **Azure**: http://169.254.169.254/metadata/attested/document?api-version=2020-09-01
   * **GCP**: http://metadata/computeMetadata/v1/instance/service-accounts/default/identity

> **Note**
> On some instances, like AWS, we can also use the IPv6 address to fetch the metadata

3. Send this metadata json blob to the contract server at:

   * https://contract.canonical.com/v1/clouds/CLOUD-TYPE/token

   Where CLOUD-TYPE is the cloud name we identified on step 1.

   The contract server will verify if the metadata is signed correctly based on the cloud
   it is stored. Additionally, some other checks are performed to see if the metadata is valid.
   For example, the contract server checks the product id provided in the metadata is a
   valid product. If any problems is found on the metadata, the contract server will produce
   an error response.

4. After the contract server validates the metadata, it returns a token that will be used
   to attach the machine to a pro subscription. To attach the machine we will reach the
   following contract server endpoint:

   * https://contract.canonical.com/v1/context/machines/token

   We will pass the token provided on step 3 as header bearer token for this request

5. The contract returns a json specification based on the provided token. This json
   contains all the directives the pro client needs to setup the machine and enable
   the necessary services the token is associated with.

6. Disable the ubuntu-advantage [daemon](../explanations/what_is_the_daemon.md).
   If the machine is detached, this daemon will be started again.

Additionally, you can disable the `pro auto-attach` command by adding
the following lines on your `uaclient.conf` configuration file, (by default located at
`/etc/ubuntu-advantage/uaclient.conf`):

```bash
features:
  disable_auto_attach: true
```

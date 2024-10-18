# Use the contracts staging environment

You can change the contract server that the Pro Client will use by setting the
following option in your `uaclient.conf` configuration file, (by default located at
`/etc/ubuntu-advantage/uaclient.conf`).

```yaml
contract_url: https://contracts.staging.canonical.com
```

> **Note**
> You might be using a local `uaclient.conf` file when running the pro client.
> If that is the case, remember to change that file instead.

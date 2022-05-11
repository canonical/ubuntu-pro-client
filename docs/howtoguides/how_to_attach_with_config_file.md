# How to attach with a configuration file

To attach with a configuration file, you must run `ua attach` with the `--attach-config` flag,
passing the path of the configuration file you intend to use.

When using `--attach-config` the token must be passed in the file rather than on the command line. This is useful in situations where it is preferred to keep the secret token in a file.

Optionally, the attach config file can be used to override the services that are automatically enabled as a part of the attach process.

An attach config file looks like this:
```yaml
token: YOUR_TOKEN_HERE  # required
enable_services:        # optional list of service names to auto-enable
  - esm-infra
  - esm-apps
  - cis
```

And can be passed on the cli like this:
```shell
sudo ua attach --attach-config /path/to/file.yaml
```

(configure_proxies)=
# How to configure a proxy

The Ubuntu Pro Client can be configured to use an HTTP/HTTPS proxy as needed
for network requests. It will also honor the `no_proxy` environment variable
(if set) to avoid using local proxies for certain outbound traffic. In
addition, the Ubuntu Pro Client will automatically set up proxies for all
programs required for enabling Ubuntu Pro services. This includes APT, Snaps,
and Livepatch.

## HTTP/HTTPS proxies

To configure standard HTTP and/or HTTPS proxies, run the following commands:

```console
$ sudo pro config set http_proxy=http://host:port
$ sudo pro config set https_proxy=https://host:port
```

After running the above commands, Ubuntu Pro Client will:

1. Verify that the proxy is working by using it to reach `api.snapcraft.io`
2. Configure itself to use the given proxy for all future network requests
3. Configure `snapd` (if `snapd` is installed) to use the given proxy
4. Configure Livepatch (if Livepatch has already been enabled) to use the given
   proxy
   1. If Livepatch is enabled after the `config` command, Ubuntu Pro Client
      will configure Livepatch to use the given proxy at that time.

To remove HTTP/HTTPS proxy configuration, run the following:

```console
$ sudo pro config unset http_proxy
$ sudo pro config unset https_proxy
```

After running the above commands, Ubuntu Pro Client will also remove proxy
configuration from `snapd` (if installed) and Livepatch (if enabled).

## APT proxies

APT proxy settings are configured separately. To have Ubuntu Pro Client manage
your global APT proxy configuration, run the following commands:

```console
$ sudo pro config set global_apt_http_proxy=http://host:port
$ sudo pro config set global_apt_https_proxy=https://host:port
```

After running the above commands, Ubuntu Pro Client will:

1. Verify that the proxy works by using it to reach `archive.ubuntu.com` or
   `esm.ubuntu.com`.
2. Configure APT to use the given proxy by writing an apt configuration file to
   `/etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy`.

```{caution}
Any configuration file that comes later in the `apt.conf.d`
directory could override the proxy configured by the Ubuntu Pro Client.
```

To remove the APT proxy configuration, run the following:

```
$ sudo pro config unset global_apt_http_proxy
$ sudo pro config unset global_apt_https_proxy
```

```{attention}
Starting in version 27.9, APT proxy config options changed.
The old settings: `apt_http_proxy` and `apt_https_proxy` will still work and
will be treated the same as `global_apt_http_proxy` and
`global_apt_https_proxy`, respectively.
```

### Pro-service-only APT proxies

To set an APT proxy that will only be used for Ubuntu Pro services, use the
following commands instead:

```console
$ sudo pro config set ua_apt_http_proxy=http://host:port
$ sudo pro config set ua_apt_https_proxy=https://host:port
```

## Authenticate your proxy server

If your proxy server requires authentication, you can pass the credentials
directly in the URL when setting the configuration, as in:

```
$ sudo pro config set https_proxy=https://username:password@host:port
```

## Check the configuration

To see which proxies Ubuntu Pro Client is currently configured to use, you can
use the `show` command.

```console
$ sudo pro config show
```

The above will output something that looks like the following if there are
proxies set:

```
http_proxy             http://proxy
https_proxy            https://proxy
global_apt_http_proxy  http://aptproxy
global_apt_https_proxy https://aptproxy
```

Or it may look like this if there aren’t any proxies set:

```
http_proxy             None
https_proxy            None
global_apt_http_proxy  None
global_apt_https_proxy None
```

# How to configure proxies

The Ubuntu Pro Client can be configured to use an HTTP/HTTPS proxy as needed for network requests. It will
also honor the `no_proxy` environment variable if set to avoid using local proxies for certain
outbound traffic. In addition, the Ubuntu Pro Client will automatically set up proxies for all programs
required for enabling Ubuntu Pro services. This includes APT, Snaps, and Livepatch.

## HTTP/HTTPS Proxies

To configure standard HTTP and/or HTTPS proxies, run the following commands:

```console
$ sudo pro config set http\_proxy=http://host:port
$ sudo pro config set https\_proxy=https://host:port
```

After running the above commands, Ubuntu Pro Client:

1. Verifies that the proxy is working by using it to reach `api.snapcraft.io`
2. Configures itself to use the given proxy for all future network requests
3. If snapd is installed, configures snapd to use the given proxy
4. If Livepatch has already been enabled, configures Livepatch to use the given proxy
   1. If Livepatch is enabled after this command, Ubuntu Pro Client will configure
      Livepatch to use the given proxy at that time.

To remove HTTP/HTTPS proxy configuration, run the following:

```console
$ sudo pro config unset http\_proxy
$ sudo pro config unset https\_proxy
```

After running the above commands, Ubuntu Pro Client will also remove proxy
configuration from snapd (if installed) and Livepatch (if enabled).

## APT Proxies

APT proxy settings are configured separately. To have Ubuntu Pro Client manage your
APT proxy configuration, run the following commands:

```console
$ sudo pro config set apt\_http\_proxy=http://host:port
$ sudo pro config set apt\_https\_proxy=https://host:port
```

After running the above commands, Ubuntu Pro Client:

1. Verifies that the proxy works by using it to reach `archive.ubuntu.com` or `esm.ubuntu.com`.
2. Configures APT to use the given proxy by writing an apt configuration file to
   `/etc/apt/apt.conf.d/90ubuntu-advantage-aptproxy`.

```{caution}
Any configuration file that comes later in the apt.conf.d
directory could override the proxy configured by the Ubuntu Pro Client.
```

To remove the APT proxy configuration, run the following:

$ sudo pro config unset apt\_http\_proxy
$ sudo pro config unset apt\_https\_proxy

```{attention}
Starting in version 27.9, APT proxy config options changed.
You will be able to set global apt proxies that affect the whole system
using the fields `global_apt_http_proxy` and `global_apt_https_proxy`.
Alternatively, you could set apt proxies only for Ubuntu Pro related services with the
fields `ua_apt_http_proxy` and `ua_apt_https_proxy`.
```

## Authenticating

If your proxy server requires authentication, you can pass
the credentials directly in the URL when setting the
configuration, as in:

$ sudo pro config set https\_proxy=https://username:password@host:port

## Checking the configuration

To see what proxies Ubuntu Pro Client is currently configured to use, you can use the show command.

```console
$ sudo pro config show
```

The above will output something that looks like the following if there are proxies set:

```
http_proxy      http://proxy
https_proxy     https://proxy
apt_http_proxy  http://aptproxy
apt_https_proxy https://aptproxy
```

Or it may look like this if there aren’t any proxies set:

```
http_proxy      None
https_proxy     None
apt_http_proxy  None
apt_https_proxy None
```

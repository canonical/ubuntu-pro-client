# How to configure proxies

The UA Client can be configured to use an http/https proxy as needed for network requests.

In addition, the UA Client will automatically set up proxies for all programs required for enabling Ubuntu Advantage services. This includes APT, Snaps, and Livepatch.

Proxies can be set using the `ua config set` command.

HTTP/HTTPS proxies are set using the fields `http_proxy` and `https_proxy`, respectively. The values for these fields will also be used for Snap and Livepatch proxies.

APT proxies are defined separately. You can set global apt proxies that affect the whole system using the fields `apt_http_proxy` and `apt_https_proxy`.

> Starting in to-be-released Version 27.9, APT proxies config options will change. You will be able to set global apt proxies that affect the whole system using the fields `global_apt_http_proxy` and `global_apt_https_proxy`. Alternatively, you could set apt proxies only for UA related services with the fields `ua_apt_http_proxy` and `ua_apt_https_proxy`.

The format for the proxy configuration values is:

`<protocol>://[<username>:<password>@]<fqdn>:<port>`

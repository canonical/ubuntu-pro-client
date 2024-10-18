# How to permanently detach Pro instances

## TL;DR

1. Modify the client configuration file, normally `/etc/ubuntu-advantage/uaclient.conf`,
to contain:

    ```yaml
    features:
      disable_auto_attach: true
    ```

2. Perform a `sudo pro detach --assume-yes`.

## Explanation

On Pro instances, a `pro detach` won't permanently detach them as,
the instance will be reauto-attached on the next boot (on non GCE instances)
or immediately (on GCE instances due to the daemon).

The config in step 1 will prevent the [daemon](../../systemd/ubuntu-advantage.service)
and the a [service](../../systemd/ua-auto-attach.service) at next boot to auto-reattach.

If you want to allow the instance to reauto attach by itself, then remove or set to false
`disable_auto_attach` in the configuration file.

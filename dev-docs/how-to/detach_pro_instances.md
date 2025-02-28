# How to permanently detach Pro instances

1. Modify the client configuration file, normally
   `/etc/ubuntu-advantage/uaclient.conf`, to contain:

   ```yaml
   features:
     disable_auto_attach: true
   ```

2. Run
   ```shell
   sudo pro detach --assume-yes`
   ```

## Explanation

On Pro instances, a `pro detach` won't permanently detach the instance since
it will be automatically re-attached on the next boot (on non-GCE instances)
or immediately (on GCE instances due to the daemon).

The configuration in step 1 will
[prevent the daemon](../explanation/autoattach_mechanisms.md) and the
[autoattach service](../../systemd/ua-auto-attach.service) from automatically
re-attaching at next boot.

If you want to allow the instance to automatically re-attach by itself, then
remove or set `disable_auto_attach` to `false` in the configuration file.

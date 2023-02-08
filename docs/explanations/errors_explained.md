# Errors you may encounter and their meaning

If you encounter an error or warning message from Pro Client that you don't understand and cannot find it in this document, please click "Have a question?" at the top of the page and let us know so that we can add it.

## User Configuration Migration in version 27.14

Version 27.14 of Ubuntu Pro Client changed how some user configuration settings are stored on disk. It moved several settings out of `/etc/ubuntu-advantage/uaclient.conf` and into a file managed solely by the `pro config {set,unset,show}` subcommands.

Most settings should've gotten automatically migrated to the new file when Pro Client upgraded. If something failed you may see one of the following messages:

### Migration error 1
**Error message:**
```
Warning: Failed to load /etc/ubuntu-advantage/uaclient.conf
         No automatic migration will occur.
         You may need to use "pro config set" to re-set your settings.
```

**Where you'll see it:**

During an `apt upgrade` or `apt install ubuntu-advantage-tools`

**What does it mean:**

This means that `/etc/ubuntu-advantage/uaclient.conf` was unable to be read or unable to be parsed as yaml during the migration.

**What you can do about it:**

Check the contents of `/etc/ubuntu-advantage/uaclient.conf`.
1. Ensure it is valid yaml
2. For any setting that is nested under `ua_config`:
  - If you modified the value in the past: run `pro config set field_name=your_custom_value`
  - delete the setting from `/etc/ubuntu-advantage/uaclient.conf`
  - delete the `ua_config:` line from `/etc/ubuntu-advantage/uaclient.conf`

### Migration error 2
**Error message:**
```
Warning: Failed to migrate user_config from /etc/ubuntu-advantage/uaclient.conf
         Please run the following to keep your custom settings:
           pro config set example=example
```

**Where you'll see it:**

During an `apt upgrade` or `apt install ubuntu-advantage-tools`

**What does it mean:**

This means that `/var/lib/ubuntu-advantage/user-config.json` was unable to be written or a json serialization error occurred.

**What you can do about it:**

Run each of the `pro config set` commands recommended in the warning message.

### Migration error 3
**Error message:**
```
Warning: Failed to migrate /etc/ubuntu-advantage/uaclient.conf
         Please add following to uaclient.conf to keep your config:
           example: example
```

**Where you'll see it:**

During an `apt upgrade` or `apt install ubuntu-advantage-tools`

**What does it mean:**

This means that `/etc/ubuntu-advantage/uaclient.conf` was unable to be written or a yaml serialization error occurred.

**What you can do about it:**

Ensure that the settings listed in the warning output make it into your new uaclient.conf.

### Log warning in versions >=27.14~

**Error message:**
```
legacy "ua_config" found in uaclient.conf
```

**Where you'll see it:**

In `/var/log/ubuntu-advantage.log` after using the `pro` cli.

**What does it mean:**

This means that there are still settings nested under `ua_config` in `/etc/ubuntu-advantage/uaclient.conf`. These will still be honored, but support may be removed in the future.

**What you can do about it:**

Check the contents of `/etc/ubuntu-advantage/uaclient.conf`.
For any setting that is nested under `ua_config`:
- If you modified the value in the past: run `pro config set field_name=your_custom_value`
- delete the setting from `/etc/ubuntu-advantage/uaclient.conf`
- delete the `ua_config:` line from `/etc/ubuntu-advantage/uaclient.conf`

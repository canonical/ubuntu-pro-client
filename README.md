# ubuntu-advantage tool

Script to enable the Ubuntu ESM (Extended Security Maintenance) archive for Precise.


## Enabling the ESM archive

To enable the archive, run:

```bash
$ sudo ubuntu-advantage enable-esm <token>
$ sudo apt-get update
```

where the `token` is in the form `<user>:<password>`.


## Disabling the ESM archive

To disable the archive, run:

```bash
$ sudo ubuntu-advantage disable-esm
$ sudo apt-get update
```

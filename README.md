# ubuntu-advantage tool

[![Build Status](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script.svg?branch=master)](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script)

Script to enable the Ubuntu ESM (Extended Security Maintenance) archive for Precise.


## Enabling the ESM archive

To enable the archive, run:

```bash
$ sudo ubuntu-advantage enable-esm <token>
```

where the `token` is in the form `<user>:<password>`.


## Disabling the ESM archive

To disable the archive, run:

```bash
$ sudo ubuntu-advantage disable-esm
```

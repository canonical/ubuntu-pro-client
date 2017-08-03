# ubuntu-advantage tool

[![Build Status](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script.svg?branch=master)](https://travis-ci.org/CanonicalLtd/ubuntu-advantage-script)

This tool is used to enable or disable specific Ubuntu Advantage offerings from Canonical.


## The ESM archive
Ubuntu Extended Security Maintenance archive. See https://ubuntu.com/esm for more information.

To enable the archive, run:

```bash
$ sudo ubuntu-advantage enable-esm token
```

where the `token` is in the form `user:password`.

To disable the archive, run:

```bash
$ sudo ubuntu-advantage disable-esm
```

## Livepatch (Canonical Livepatch Service)
Managed live kernel patching. For more information, visit https://www.ubuntu.com/server/livepatch

To enable live patching on your system, run:

```bash
$ sudo ubuntu-advantage enable-livepatch token
```

The token can be obtained by visiting https://ubuntu.com/livepatch

To disable livepatch, run:

```bash
$ sudo ubuntu-advantage disable-livepatch
```

If you also want to remove the canonical-livepatch snap, you can pass the `-r` option to `disable-livepatch`.

## Testing

Unit tests & lint:

```bash
$ tox
```

Dep8 Tests:

```
# To test on 16.04:
$ autopkgtest --shell-fail . -- lxd ubuntu:xenial
```

# How to generate Ubuntu Advantage user documentation

To build the docs for Ubuntu Advantage, you can use a dedicated `tox` command for it.
You can install `tox` on your machine by running the `make test` command. Once tox is
installed just run the command:

```console
$ tox -e docs
```

The command will generate the html pages inside `docs/build`

# How to generate Ubuntu Pro Client user documentation

To build the docs for Ubuntu Pro Client, you can use a dedicated `tox` command for it.
You can install `tox` on your machine by running the `make test` command. Once tox is
installed just run the command:

```console
$ tox -e docs
```

The command will generate the html pages inside `docs/build`

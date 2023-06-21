# Code Formatting

The `ubuntu-pro-client` code base is formatted using
[black](https://github.com/psf/black), and imports are sorted with
[isort](https://github.com/PyCQA/isort).  When making changes, you
should ensure that your code is blackened and isorted, or it will
be rejected by CI.
Formatting the whole codebase is as simple as running:

```shell
black uaclient/
isort uaclient/
```

To make it easier to avoid committing incorrectly formatted code, this
repo includes configuration for [pre-commit](https://pre-commit.com/)
which will stop you from committing any code that isn't blackened.  To
install the project's pre-commit hook, install `pre-commit` and run:

```shell
pre-commit install
```

(To install `black` and `pre-commit` at the appropriate versions for
the project, you should install them via `dev-requirements.txt`.)

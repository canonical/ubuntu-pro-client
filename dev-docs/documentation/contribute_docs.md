# How to contribute documentation

The process for contributing to the docs is largely the same as for code,
except that for cosmetic changes to the documentation (spelling, grammar, etc)
you can also use the GitHub web interface to submit changes as quick PRs.

If you've found a problem with our documentation - whether it's a spelling or
grammatical issue, or you were not able to find the answer to your problem,
you can click on the "Give feedback" button at the top of that page to report
it to us with a GitHub issue. We are always looking for ways to improve our
documentation, so letting us know what you think of it is a very valuable way
to contribute!

## Our branch structure

To facilitate the package release process and keep the documentation maintained
in the same repository as the codebase, there are two separate branches for the
docs:

- The `docs` branch, where the latest documentation is kept. This branch is
  used to track releases and is published in `Read The Docs`;
- The `docs-devel` branch, where the documentation of upcoming features and
  changes is kept until they are ready to be released.

When a pull request with improvements or new content to the documentation
contains features which are not released yet, it should target the
`docs-devel` branch. Fixes, improvements, and content for existing features can
target the `docs` branch directly, so they are published immediately after the
pull request is merged.

## Building the docs locally

To build the docs for Ubuntu Pro Client, you can use the `make` command.
Switch to the `docs` (or `docs-devel`) branch and install the dependencies:

```bash
$ git checkout docs
$ make install
```

If you only wish to build the docs once (e.g., to have a local copy on your
machine) then run:

```bash
$ make html
```

The `html` command will generate the HTML pages inside `docs/build`.
The makefile target will build the documentation for you using Sphinx. Once
built, the HTML files will be viewable in `docs/build/html/`. Use your web
browser to open `index.html` to preview the site.

Alternatively, if you are working on a documentation change you can use the
command:

```bash
$ make run
```

This will build *and serve* the documentation at http://127.0.0.1:8000 -- this
gives you a live preview of any changes you make (and save) to the
documentation without needing to continually rebuild.

## Docs structure and organisation

We follow the [principles of Diataxis](https://diataxis.fr/) in our
documentation. When writing new docs, try to consider the purpose of the
document and how the reader will probably use it. You should have an idea in
mind before you start about what style of page you want to write, according to
the Diataxis framework:

* A tutorial, to guide users through some aspect of the Pro Client in a
  sandboxed environment.
* A how-to guide, providing the steps to achieve a particular task.
* An explanation of a particular topic, or
* A reference page.

As much as possible, we want the Pro Client documentation to be easy to
navigate, so we try to avoid repetition. New documentation should be created to
fit into the hierarchy of pages which already exist. If you are unsure of where
the page should go, or think we need to rearrange our current documentation,
please submit an issue so that we can have a discussion about it.

Whether you are editing an existing page, or creating a new one, you should
follow our [style guide](styleguide.md) to ensure that any delays in publishing
are not due to minor inconsistencies in style. 

### Getting advice

If you are in any doubt, please contact our team's
[Technical Author (Sally)](https://github.com/s-makin) for guidance. If you
would like her to review any documentation, she would be very happy to help!
Please also tag her as a reviewer on any PR that contains documentation
elements.

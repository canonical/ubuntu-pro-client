# Documentation

Our docs are hosted on [Read the Docs](https://readthedocs.com/). This page
will explain how to contribute to the docs and build them locally.

The documentation is *primarily* written in standard Markdown, but pages can
be written in reStructuredText if you prefer.

We also use the
[MyST-Parser Sphinx extension](https://myst-parser.readthedocs.io/en/latest/intro.html).
This causes all Markdown (.md) files to be parsed as MyST, and
[enables the use of directives](https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html),
which can be awkward to achieve in standard Markdown.

## Branches

To facilitate the package release process and keep the documentation maintained
in the same repository as the codebase, there are two separate branches for the
docs:
- The `docs` branch, where the latest documentation is kept, used to track
  releases and publish it in `Read The Docs`;
- The `docs-devel` branch, where the documentation of upcoming features and changes is kept until they are ready to be released.

When a pull request with improvements or new content to the documentation
contains features which are not released yet, it should target the
`docs-devel` branch. Fixes, improvements, and content for existing features can
target the `docs` branch directly, so they are published immediately after the
pull request is merged.

## Building the docs

To build the docs for Ubuntu Pro Client, you can use the `make` command.
Switch to the `docs` (or `docs-devel`) branch and make sure to install the
dependencies:

```
$ git checkout docs
$ make install
```

When the environment is set up, run:

```
$ make build
```

The command will generate the HTML pages inside `docs/build`. The makefile
target will build the documentation for you using Sphinx.

Once built, the HTML files will be viewable in `docs/build/html/`. Use your web
browser to open `index.html` to preview the site.

## Style guide

We use the [Canonical style guide](https://docs.ubuntu.com/styleguide/en) in
our documentation, which is summarised below -- with a few additions relevant
to our docs.

### Language

Where possible, text should be written in UK English. However, discretion and
common sense can both be applied. For example, where text refers to code
elements that exist in US English, the spelling of these elements should not
be changed to UK English.

### Voice

Try to use active voice where possible, rather than the passive voice. The
active voice is generally more concise and easier to read. As an example, you
could say "we recommend" (active) rather than "it is recommended that"
(passive). 

### Headings

Headings should be written in sentence case. This means that only the first
letter is capitalised (unless the header text refers to e.g., a product name
that would normally be capitalised, such as "Ubuntu Pro Client").

Ensure that you do not skip header levels when creating your document
structure, i.e., that a section is followed by a subsection, and not a
sub-subsection. Skipping header levels can lead to de-ranking of pages in
search engines.

Try to craft your headings to be descriptive, but as short as possible, to help
readers understand what content to expect if they click on it.

### Line length

Please keep the line lengths to a maximum of **79** characters. This ensures
that the pages and tables do not get so wide that side scrolling is required.

### Links

Where possible, use contextual text in your links to aid users with screen
readers and other accessibility tools. For example, "check out our
[documentation style guide](#links) is preferable to "click
[here](#links) for more".

### Code blocks

Our documentation uses the
[Sphinx extension "sphinx-copybutton"](https://sphinx-copybutton.readthedocs.io/en/latest/),
which creates a small button on the right-hand side of code blocks for users to
copy the code snippets we provide.

The copied code will strip out any prompt symbols so that users can
paste commands directly into their terminal. For user convenience, please
ensure that if you show any code output, it is presented in a separate code
block to the commands.

Please also specify the language used in your code block, to make sure it
renders with the correct syntax highlighting.

### Vertical whitespace

One newline between each section helps ensure readability of the documentation
source code. Keeping paragraphs relatively short (up to ~5-6 sentences) aids in
keeping the text readable when rendered to a web page. Some rST elements also
require an empty newline before and after, so for consistency, ensure that all
elements (tables, images, headers, etc) have a newline before and after.

### Acronyms and jargon

Acronyms are always capitalised (e.g., JSON, YAML, QEMU, LXD) in text.

The first time an acronym is used on a page, it is best practice to introduce
it by showing the expanded name followed by the acronym in parentheses. E.g.,
Quick EMUlator (QEMU). If the acronym is *very* common (e.g., URL, HTTP), or
you provide a link to a documentation page with these details, you do not need
to include them.

Avoid using jargon unless absolutely necessary, to keep our documentation
accessible to as wide a range of users as possible. If jargon is unavoidable,
consider including brief explanations to help the user keep up with the
material.

### Admonitions and callouts

Notes, warnings, or other information you wish to draw the reader's attention
to can be called out in an admonition block. If you are writing your code in
Markdown, this is where the MyST extension comes in handy. Here is an example:

````
  ```{note}
  The options are: note, important, hint, seealso, tip, attention, caution,
  warning, danger, and error.
  ```{warning}
  Although it's possible to nest admonitions inside each other, it's better to
  avoid doing that unless it's strictly necessary!
  ```
````

```{note}
The options are: note, important, hint, seealso, tip, attention, caution,
warning, danger, and error.
```{warning}
Although it's possible to nest admonitions inside each other, it's better to
avoid doing that unless it's strictly necessary!
```

## Organisation

We follow the [principles of Diataxis](https://diataxis.fr/) in our
documentation. When writing new docs, try to consider the purpose of the
document and how the reader will probably use it. This will help you to decide
which section it belongs in.

### Getting advice

If you are in any doubt, please contact our team's
[Technical Author (Sally)](https://github.com/s-makin) for guidance. If you
would like her to review any documentation, she would be very happy to help!
Please also tag her as a reviewer on any PR that contains documentation
elements.

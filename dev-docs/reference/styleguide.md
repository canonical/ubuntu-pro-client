# Documentation style guide

Our documentation is written in
[reStructuredText](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
and hosted on [Read the Docs](https://readthedocs.com/).

## General tips and style guide

Documentation consistency (in terms of writing style) is vital for a good user
experience. We use the [Canonical style guide](https://docs.ubuntu.com/styleguide/en)
in our documentation, which is summarised below -- with a few additions.

To make it more straightforward to publish your contribution, we recommend that
you:

* Use a spell checker (set to en-us).
* Be concise and to-the-point in your writing.
* Check your links and test your code snippets to make sure they work as
  expected.
* Link back to other (reputable) pages on a topic, rather than repeating their
  content.
* Try not to assume that your reader will have the same knowledge as you. If
  you’re covering a new topic (or something complicated) then try to briefly
  explain, or link to, things the average reader may not know.
* If you have used some references you think would be generally helpful to your
  reader, feel free to include a “Further reading” section at the end of the
  page.
* If your list items are longer than a sentence or two each, consider using
  sub-headings instead, so that they appear in the in-page navigation menu (on
  the right-hand side of the screen).

### Language

Text should be written in US English. 

### Voice

Try to use active voice where possible, rather than the passive voice. The
active voice is generally more concise and easier to read. As an example, you
could say "we recommend" (active) rather than "it is recommended that"
(passive). 

### Headings

Headings must be written in sentence case. This means that only the first
letter is capitalised (unless the header text refers to e.g., a product name
that would normally be capitalised, such as "Ubuntu Pro Client").

Avoid skipping heading levels in your document structure, i.e., a level 2
header should always be followed by a level 3 sub-header and not level 4.

Try to craft your headings to be descriptive, but as short as possible, to help
readers understand what content to expect on the page.

### Line length

Please keep the line lengths to a maximum of **79** characters where possible.
This ensures that the pages and tables do not get so wide that side scrolling
is required.

### Links

Use contextual text in your links to aid users with screen readers and other
accessibility tools. For example, use something like "check out our
[documentation style guide](#links) rather than "click [here](#links) for more"
because it provides a larger link area and also helps readers to understand
what the link contains.

### Code blocks

Our documentation uses the
[Sphinx extension "sphinx-copybutton"](https://sphinx-copybutton.readthedocs.io/en/latest/),
which creates a small button on the right-hand side of code blocks for users to
copy the code snippets we provide.

You can create a code block by using the ``.. code-block::`` directive and
including the language (for syntax highlighting). E.g:

```
.. code-block:: yaml

   Some code block here
```

There must be an empty line before AND after the `code-block` directive, and
the code block contents must be indented at least three spaces to be
recognised.

Using "text" as the language is useful for displaying command output or plain
text, since it does not highlight anything.

The copied code will strip out any prompt symbols so that users can
paste commands directly into their terminal. For user convenience, please
ensure that if you show any code output, it is presented in a separate code
block to the commands. The output should be preceded with a small description
that explains what’s happening. For example:

```
.. code-block:: bash

   uname -r

Produces the following output:

.. code-block:: text

   4.14.151
```

Use a double backtick to mark inline commands and other string literals, like
paths to files. This will render them in monospaced font within the paragraph.

### Vertical empty space

One new line between each section ensures readability of the documentation
source code. Short paragraphs (up to ~5-6 sentences) aids in keeping text
readable when rendered to a web page.

Some rST elements require an empty line before and after, so for consistency,
ensure that all elements (tables, images, headers, etc) have a new line before
and after.

### Acronyms and jargon

Acronyms are always capitalised (e.g., JSON, YAML, QEMU, LXD) in text.

The first time an acronym is used on a page, introduce it by showing the
expanded name followed by the acronym in parentheses. E.g., Quick EMUlator
(QEMU). If the acronym is *very* common (e.g., URL, HTTP), or you provide a
link to a documentation page with these details, you do not need to include
them.

Avoid using jargon unless absolutely necessary, to keep our documentation
accessible to as wide a range of users as possible. If jargon is unavoidable,
include brief explanations to help the user understand the material.

### Admonitions and callouts

Notes, warnings, or other information you wish to draw the reader's attention
to can be called out in an admonition block. Here is an example:

```
.. note::

   The options are: ``note``, ``important``, ``hint``, ``seealso``, ``tip``,
   ``attention``, ``caution``, ``warning``, ``danger``, and ``error``.
      
   .. warning::
      Although it's possible to nest admonitions like this, it's better to
      avoid doing that unless it's strictly necessary!
```

In general, it's best to use as few admonitions as possible. Having too many
of these boxes on the page can lead to users ignoring them. 


### Add a diagram

Our documentation builds are configured to allow the use of
[mermaid](https://mermaid.js.org/) for diagrams.

Mermaid blocks can be included in a reStructuredText file with the following
syntax:

```
.. mermaid::
   <code block here>
```

If you have trouble getting the Mermaid diagram to render, check to make sure
you have included empty lines before and after the ``.. mermaid::`` line, and
that your Mermaid code is indented as it would be for a code block. 

These links may be helpful to get started if you're new to Mermaid:

- `The mermaid live online editor <https://mermaid.live/edit>`_
- `Mermaid syntax for creating a flowchart <https://mermaid.js.org/syntax/flowchart.html?id=flowcharts-basic-syntax>`_

### Getting advice

If you are in any doubt, please contact our team's
[Technical Author (Sally)](https://github.com/s-makin) for guidance. If you
would like her to review any documentation, she would be very happy to help!
Tag her as a reviewer on any PR that contains documentation.

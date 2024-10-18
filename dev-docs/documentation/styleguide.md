# Documentation style guide

Our documentation is *primarily* written in standard Markdown, but pages can
be written in reStructuredText if you prefer. Our docs are hosted on
[Read the Docs](https://readthedocs.com/). 

We also use the
[MyST-Parser Sphinx extension](https://myst-parser.readthedocs.io/en/latest/intro.html).
This causes all Markdown (.md) files to be parsed as MyST, and
[enables the use of directives](https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html),
which can be awkward to achieve in standard Markdown.

## General tips and style guide

Documentation consistency (in terms of writing style) is vital for a good user
experience. We use the [Canonical style guide](https://docs.ubuntu.com/styleguide/en)
in our documentation, which is summarised below -- with a few additions
relevant to our docs.

To make it more straightforward to publish your contribution, we recommend that
you:

* Use a spell checker (set to en-GB).
* Be concise and to-the-point in your writing.
* Check your links and test your code snippets to make sure they work as
  expected.
* Link back to other (reputable) pages on a topic, rather than repeating their
  content.
* Expand your acronyms the first time they appear on the page, e.g.
  JavaScript Object Notation (JSON).
* Try not to assume that your reader will have the same knowledge as you. If
  you’re covering a new topic (or something complicated) then try to briefly
  explain, or link to, things the average reader may not know.
* If you have used some references you think would be generally helpful to your
  reader, feel free to include a “Further reading” section at the end of the
  page.
* Unless a list item includes punctuation, don’t end it with a full stop. If
  one item in the list needs a full stop, add one to all the items.
  
  If your list items are longer than a sentence or two each, consider whether
  it might be better to use sub-headings instead, so that they appear in the
  in-page navigation menu (on the right-hand side of the screen).

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

Try not to skip heading levels in your document structure, i.e., a level 2
header (##) should always be followed by a level 3 sub-header (###) not level
4.Skipping header levels can lead to de-ranking of pages in search engines.

Try to craft your headings to be descriptive, but as short as possible, to help
readers understand what content to expect on the page.

### Line length

Please keep the line lengths to a maximum of **79** characters. This ensures
that the pages and tables do not get so wide that side scrolling is required.

### Links

Where possible, use contextual text in your links to aid users with screen
readers and other accessibility tools. For example, "check out our
[documentation style guide](#links) is preferable to "click
[here](#links) for more" because it provides a larger link area and also helps
readers to understand what the link contains.

### Code blocks

Our documentation uses the
[Sphinx extension "sphinx-copybutton"](https://sphinx-copybutton.readthedocs.io/en/latest/),
which creates a small button on the right-hand side of code blocks for users to
copy the code snippets we provide.

You can create a code block by using three backticks ``` and including the
language (for syntax highlighting):

```
  ```yaml
  Some code block here
  ```
```

Using "text" as the language is useful for displaying command output or plain
text, since it does not highlight anything.

The copied code will strip out any prompt symbols so that users can
paste commands directly into their terminal. For user convenience, please
ensure that if you show any code output, it is presented in a separate code
block to the commands. The output should be preceded with a small description
that explains what’s happening. For example:

```
  ```bash
  uname -r
  ```

  Produces the following output:

  ```text
  4.14.151
  ```
```

Use a single backtick to mark inline commands and other string literals, like
paths to files. This will render them in monospaced font within the paragraph.

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

### Getting advice

If you are in any doubt, please contact our team's
[Technical Author (Sally)](https://github.com/s-makin) for guidance. If you
would like her to review any documentation, she would be very happy to help!
Please also tag her as a reviewer on any PR that contains documentation
elements.

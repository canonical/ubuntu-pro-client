.. _spellcheck:

How to spellcheck messages
**************************

We have CI running on every PR which looks for spelling errors in our English
messages, but it is often useful to run it locally as well.

First install ``hunspell``:

.. code-block::

   sudo apt install hunspell

Then run it on our messages module using our list of extra allowed words:

.. code-block::

   hunspell -p ./tools/spellcheck-allowed-words.txt -l ./uaclient/messages/__init__.py

That particular ``hunspell`` command will print any incorrectly-spelled words
to stdout.

``hunspell`` has other options including an interactive mode for fixing errors.
Check out the
`hunspell documentation <https://github.com/hunspell/hunspell#documentation>`_
for more information.

If ``hunspell`` reports something is spelled incorrectly, but we need to spell
that word a particular way for some reason, you can add that word to
`the exception list <https://github.com/canonical/ubuntu-pro-client/blob/main/tools/spellcheck-allowed-words.txt>`_.

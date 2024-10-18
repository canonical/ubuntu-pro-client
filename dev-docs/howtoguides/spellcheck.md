# How to spellcheck messages

We have CI that runs on every PR which looks for spelling errors in our English messages, but it is often useful to run it locally as well.

First install `hunspell`.
```
sudo apt install hunspell
```

Then run it on our messages module using our list of extra allowed words.

```
hunspell -p ./tools/spellcheck-allowed-words.txt -l ./uaclient/messages/__init__.py
```

That particular `hunspell` command will print any incorrectly spelled words to stdout.

`hunspell` has other options including an interactive mode for fixing errors. Check out the [`hunspell` documentation](https://github.com/hunspell/hunspell#documentation) for more information.

If `hunspell` is saying something is spelled incorrectly, but `hunspell` is wrong, or we need to spell that word a particular way for some reason, you can add that word to `./tools/spellcheck-allowed-words.txt`.

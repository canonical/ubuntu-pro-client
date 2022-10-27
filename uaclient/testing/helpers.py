try:  # Drop try-except after xenial EOL
    from contextlib import AbstractContextManager
except ImportError:
    AbstractContextManager = object


class does_not_raise(AbstractContextManager):
    """Reentrant noop context manager.
    Useful to parametrize tests raising and not raising exceptions.

    Note: In python-3.7+, this can be substituted by contextlib.nullcontext
    More info:
    https://docs.pytest.org/en/6.2.x/example/parametrize.html?highlight=does_not_raise#parametrizing-conditional-raising

    Example:
    --------
    >>> @pytest.mark.parametrize(
    >>>     "example_input,expectation",
    >>>     [
    >>>         (1, does_not_raise()),
    >>>         (0, pytest.raises(ZeroDivisionError)),
    >>>     ],
    >>> )
    >>> def test_division(example_input, expectation):
    >>>     with expectation:
    >>>         assert (0 / example_input) is not None
    """

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

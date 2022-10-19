from contextlib import contextmanager


@contextmanager
def does_not_raise():
    """Context manager to parametrize tests raising and not raising exceptions
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
    yield

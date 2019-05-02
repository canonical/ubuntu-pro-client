import io
import logging

import pytest


@pytest.fixture
def caplog_text(request):
    """
    A fixture that returns a function that returns caplog.text

    caplog isn't available in pytest in all of our target releases; this either
    uses caplog.text if available, or a shim which replicates what it does.

    Specifically, bionic is the first Ubuntu release to contain a version of
    pytest new enough for the caplog fixture to be present.  In xenial, the
    python3-pytest-catchlog package provides the same functionality (this is
    the code that was later integrated in to pytest).  For trusty, there is no
    packaged alternative to this shim.

    (It returns a function so that the requester can decide when to examine the
    logs; if it returned caplog.text directly, that would always be empty.)
    """
    try:
        try:
            # TODO pyest 3.4 is funky and logs debug level by default
            # https://docs.pytest.org/en/features/logging.html#\
            #            incompatible-changes-in-pytest-3-4
            # write_cache debug logs are seen on Bionic in test_livepatch:
            # test_enable_false_when_can_enable_false
            caplog = request.getfixturevalue('caplog')
        except AttributeError:
            # Older versions of pytest only have getfuncargvalue, which is now
            # deprecated in favour of getfixturevalue
            caplog = request.getfuncargvalue('caplog')
        caplog.set_level(logging.INFO)

        def _func():
            return caplog.text
    except LookupError:
        # If the caplog fixture isn't available, shim something in ourselves
        root = logging.getLogger()
        root.setLevel(logging.INFO)
        handler = logging.StreamHandler(io.StringIO())
        handler.setFormatter(
            logging.Formatter(
                "%(filename)-25s %(lineno)4d %(levelname)-8s %(message)s"))
        root.addHandler(handler)

        def _func():
            return handler.stream.getvalue()

        request.addfinalizer(lambda: root.removeHandler(handler))
    return _func

import io
import logging
import sys
from typing import Any, Dict

import mock
import pytest

from uaclient import event_logger
from uaclient.config import UAConfig

# We are doing this because we are sure that python3-apt comes with the distro,
# but it cannot be installed in a virtual environment to be properly tested.
sys.modules["apt"] = mock.MagicMock()


@pytest.yield_fixture(scope="session", autouse=True)
def _subp():
    """
    A fixture that mocks util._subp for all tests.
    If a test needs the actual _subp, this fixture yields it,
    so just add an argument to the test named "_subp".
    """
    from uaclient.util import _subp

    original = _subp
    with mock.patch(
        "uaclient.util._subp", return_value=("mockstdout", "mockstderr")
    ):
        yield original


@pytest.fixture
def caplog_text(request):
    """
    A fixture that returns a function that returns caplog.text

    caplog isn't available in pytest in all of our target releases; this either
    uses caplog.text if available, or a shim which replicates what it does.

    Specifically, bionic is the first Ubuntu release to contain a version of
    pytest new enough for the caplog fixture to be present. In xenial, the
    python3-pytest-catchlog package provides the same functionality (this is
    the code that was later integrated in to pytest).

    (It returns a function so that the requester can decide when to examine the
    logs; if it returned caplog.text directly, that would always be empty.)
    """
    log_level = getattr(request, "param", logging.INFO)
    try:
        try:
            caplog = request.getfixturevalue("caplog")
        except AttributeError:
            # Older versions of pytest only have getfuncargvalue, which is now
            # deprecated in favour of getfixturevalue
            caplog = request.getfuncargvalue("caplog")
        caplog.set_level(log_level)

        def _func():
            return caplog.text

    except LookupError:
        # If the caplog fixture isn't available, shim something in ourselves
        root = logging.getLogger()
        root.setLevel(log_level)
        handler = logging.StreamHandler(io.StringIO())
        handler.setFormatter(
            logging.Formatter(
                "%(filename)-25s %(lineno)4d %(levelname)-8s %(message)s"
            )
        )
        root.addHandler(handler)

        def _func():
            return handler.stream.getvalue()

        def clear_handlers():
            logging.root.handlers = []

        request.addfinalizer(clear_handlers)
    return _func


@pytest.yield_fixture
def logging_sandbox():
    # Monkeypatch a replacement root logger, so that our changes to logging
    # configuration don't persist outside of the test
    root_logger = logging.RootLogger(logging.WARNING)

    with mock.patch.object(logging, "root", root_logger):
        with mock.patch.object(logging.Logger, "root", root_logger):
            with mock.patch.object(
                logging.Logger, "manager", logging.Manager(root_logger)
            ):
                yield


@pytest.fixture
def FakeConfig(tmpdir):
    class _FakeConfig(UAConfig):
        def __init__(
            self,
            cfg_overrides={},
            features_override=None,
            root_mode: bool = True,
        ) -> None:
            if not cfg_overrides.get("data_dir"):
                cfg_overrides.update({"data_dir": tmpdir.strpath})
            super().__init__(cfg_overrides, root_mode=root_mode)

        @classmethod
        def for_attached_machine(
            cls,
            account_name: str = "test_account",
            machine_token: Dict[str, Any] = None,
            status_cache: Dict[str, Any] = None,
            root_mode: bool = True,
        ):
            if not machine_token:
                machine_token = {
                    "availableResources": [],
                    "machineToken": "not-null",
                    "machineTokenInfo": {
                        "machineId": "test_machine_id",
                        "accountInfo": {
                            "id": "acct-1",
                            "name": account_name,
                            "createdAt": "2019-06-14T06:45:50Z",
                            "externalAccountIDs": [
                                {"IDs": ["id1"], "Origin": "AWS"}
                            ],
                        },
                        "contractInfo": {
                            "id": "cid",
                            "name": "test_contract",
                            "createdAt": "2020-05-08T19:02:26Z",
                            "effectiveFrom": "2000-05-08T19:02:26Z",
                            "effectiveTo": "2040-05-08T19:02:26Z",
                            "resourceEntitlements": [],
                            "products": ["free"],
                        },
                    },
                }

            if not status_cache:
                status_cache = {"attached": True}

            config = cls(root_mode=root_mode)
            config.machine_token_file.write(machine_token)
            config.write_cache("status-cache", status_cache)
            return config

        def override_features(self, features_override):
            if features_override is not None:
                self.cfg.update({"features": features_override})

    return _FakeConfig


@pytest.fixture
def event():
    event = event_logger.get_event_logger()
    event.reset()

    return event

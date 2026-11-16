"""Regression tests for bulk APT candidate classification (issue #3605)."""

from collections import defaultdict
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from uaclient import security_status


def test_create_updates_list_opens_apt_cache_once():
    first = SimpleNamespace(
        parent_pkg=SimpleNamespace(name="first"), ver_str="2", size=10
    )
    second = SimpleNamespace(
        parent_pkg=SimpleNamespace(name="second"), ver_str="3", size=20
    )
    versions = defaultdict(
        list, {"standard-updates": [(first, "archive"), (second, "archive")]}
    )
    cache = {"first": object(), "second": object()}
    opens = []

    @contextmanager
    def fake_preserve_cache(factory):
        opens.append(factory)
        yield cache

    class FakeDepCache:
        def __init__(self, apt_cache):
            assert apt_cache is cache

        def get_candidate_ver(self, package):
            return SimpleNamespace(ver_str="2" if package is cache["first"] else "4")

    ua_info = {"attached": False, "enabled_services": []}
    with (
        patch.object(security_status, "PreserveAptCfg", fake_preserve_cache),
        patch.object(security_status.apt_pkg, "DepCache", FakeDepCache),
        patch.object(
            security_status, "get_pkg_candidate_version",
            side_effect=AssertionError("per-update cache lookup"),
        ),
    ):
        result = security_status.create_updates_list(versions, ua_info)

    assert len(opens) == 1
    assert [row["status"] for row in result] == [
        security_status.UpdateStatus.AVAILABLE.value,
        security_status.UpdateStatus.AVAILABLE_NOT_PREFERRED.value,
    ]


def test_create_updates_list_skips_cache_for_unattached_esm():
    version = SimpleNamespace(
        parent_pkg=SimpleNamespace(name="first"), ver_str="2", size=10
    )
    versions = defaultdict(list, {"esm-apps": [(version, "archive")]})
    ua_info = {"attached": False, "enabled_services": []}
    with patch.object(
        security_status, "PreserveAptCfg",
        side_effect=AssertionError("cache should not open"),
    ):
        result = security_status.create_updates_list(versions, ua_info)
    assert result[0]["status"] == security_status.UpdateStatus.UNATTACHED.value

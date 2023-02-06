import logging

import mock
import pytest

from lib.esm_cache import main
from uaclient.exceptions import MissingSeriesOnOSReleaseFile


@mock.patch("lib.esm_cache.update_esm_caches")
class TestUpdateEsmCaches:
    def test_builds_local_cache(self, m_update_caches, FakeConfig):
        main(FakeConfig())

        assert m_update_caches.call_count == 1

    @pytest.mark.parametrize("caplog_text", [logging.ERROR], indirect=True)
    def test_log_user_facing_exception(
        self, m_update_caches, caplog_text, FakeConfig
    ):
        expected_exception = MissingSeriesOnOSReleaseFile(version="version")
        m_update_caches.side_effect = expected_exception
        main(cfg=FakeConfig())

        for line in expected_exception.msg.split("\n"):
            assert line in caplog_text()

    @pytest.mark.parametrize("caplog_text", [logging.ERROR], indirect=True)
    def test_log_exception(self, m_update_caches, caplog_text, FakeConfig):
        expected_msg = "unexpected exception"
        expected_exception = Exception(expected_msg)
        m_update_caches.side_effect = expected_exception
        main(cfg=FakeConfig())

        assert expected_msg in caplog_text()

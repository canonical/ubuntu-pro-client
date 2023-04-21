import logging

import mock
import pytest

from lib.esm_cache import main
from uaclient.exceptions import MissingSeriesOnOSReleaseFile
from uaclient.messages import MISSING_SERIES_ON_OS_RELEASE


@mock.patch("lib.esm_cache.update_esm_caches")
class TestUpdateEsmCaches:
    def test_builds_local_cache(self, m_update_caches, FakeConfig):
        main(FakeConfig())

        assert m_update_caches.call_count == 1

    @mock.patch("lib.esm_cache.LOG.error")
    def test_log_user_facing_exception(
        self, m_esm_cache_log_err, m_update_caches, FakeConfig
    ):
        expected_exception = MissingSeriesOnOSReleaseFile(version="version")
        m_update_caches.side_effect = expected_exception
        main(cfg=FakeConfig())
        expected_log_args = [
            mock.call(
                "Error updating the cache: %s",
                MISSING_SERIES_ON_OS_RELEASE.format(version="version").msg,
            )
        ]

        assert expected_log_args == m_esm_cache_log_err.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.ERROR], indirect=True)
    def test_log_exception(self, m_update_caches, caplog_text, FakeConfig):
        expected_msg = "unexpected exception"
        expected_exception = Exception(expected_msg)
        m_update_caches.side_effect = expected_exception
        main(cfg=FakeConfig())

        assert expected_msg in caplog_text()

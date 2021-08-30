import logging

import mock
import pytest

from uaclient.exceptions import NonAutoAttachImageError
from uaclient.jobs.gcp_auto_attach import gcp_auto_attach


class TestGCPAutoAttachJob:
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_auto_attach_already_attached(
        self, m_auto_attach, m_cloud_type, FakeConfig
    ):
        m_cloud_type.return_value = ("gce", None)
        cfg = FakeConfig.for_attached_machine()
        assert gcp_auto_attach(cfg) is None
        assert m_auto_attach.call_count == 0

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize(
        "cloud_type", (("gce"), ("azure"), ("aws"), (None))
    )
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_auto_attach(
        self, m_auto_attach, m_cloud_type, cloud_type, caplog_text, FakeConfig
    ):
        m_cloud_type.return_value = (cloud_type, None)
        cfg = FakeConfig()

        with mock.patch.object(type(cfg), "write_cfg") as m_write:
            cfg.gcp_auto_attach_timer = 1000
            assert gcp_auto_attach(cfg) is None

        if cloud_type != "gce":
            assert m_auto_attach.call_count == 0
            assert cfg.gcp_auto_attach_timer == 0
            assert m_write.call_count == 2
            assert (
                "Disabling gcp_auto_attach job. Not running on GCP instance"
            ) in caplog_text()

        else:
            assert cfg.gcp_auto_attach_timer == 1000
            assert m_write.call_count == 1
            assert m_auto_attach.call_count == 1

    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_job_dont_fail_if_non_auto_attach_image_error_is_raised(
        self, m_auto_attach, m_cloud_type, FakeConfig
    ):
        m_cloud_type.return_value = ("gce", None)
        m_auto_attach.side_effect = NonAutoAttachImageError("error")
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is None
        assert m_auto_attach.call_count == 1

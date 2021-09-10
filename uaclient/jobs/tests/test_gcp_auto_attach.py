import logging

import mock
import pytest

from uaclient.exceptions import NonAutoAttachImageError
from uaclient.jobs.gcp_auto_attach import (
    UAAutoAttachGCPInstance,
    gcp_auto_attach,
)


@mock.patch(
    "uaclient.jobs.gcp_auto_attach.GCP_LICENSES",
    {"ubuntu-lts": "test-license-id"},
)
class TestGCPAutoAttachJob:
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_auto_attach_already_attached(
        self, m_auto_attach, m_cloud_type, FakeConfig
    ):
        m_cloud_type.return_value = ("gce", None)
        cfg = FakeConfig.for_attached_machine()
        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 0

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize(
        "cloud_type", (("gce"), ("azure"), ("aws"), (None))
    )
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "get_licenses_from_identity")
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_platform_info")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_auto_attach(
        self,
        m_auto_attach,
        m_platform_info,
        m_get_licenses,
        m_cloud_type,
        cloud_type,
        caplog_text,
        FakeConfig,
    ):
        m_cloud_type.return_value = (cloud_type, None)
        m_get_licenses.return_value = ["test-license-id"]
        m_platform_info.return_value = {"series": "ubuntu-lts"}
        cfg = FakeConfig()

        with mock.patch.object(type(cfg), "write_cfg") as m_write:
            m_auto_attach.return_value = 0
            cfg.gcp_auto_attach_timer = 1000
            return_value = gcp_auto_attach(cfg)

        if cloud_type != "gce":
            assert m_auto_attach.call_count == 0
            assert cfg.gcp_auto_attach_timer == 0
            assert m_write.call_count == 2
            assert (
                "Disabling gcp_auto_attach job. Not running on GCP instance"
            ) in caplog_text()
            assert return_value is False

        else:
            assert cfg.gcp_auto_attach_timer == 1000
            assert m_write.call_count == 1
            assert m_auto_attach.call_count == 1
            assert return_value is True

    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "get_licenses_from_identity")
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_platform_info")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_job_dont_fail_if_non_auto_attach_image_error_is_raised(
        self,
        m_auto_attach,
        m_platform_info,
        m_get_licenses,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_get_licenses.return_value = ["test-license-id"]
        m_platform_info.return_value = {"series": "ubuntu-lts"}
        m_auto_attach.side_effect = NonAutoAttachImageError("error")
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 1

    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "get_licenses_from_identity")
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_platform_info")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_job_dont_fail_if_licenses_fail(
        self,
        m_auto_attach,
        m_platform_info,
        m_get_licenses,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_get_licenses.side_effect = TypeError("error")
        m_platform_info.return_value = {"series": "ubuntu-lts"}
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 0
        assert m_get_licenses.call_count == 1

    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "get_licenses_from_identity")
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_platform_info")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_auto_attach_license_not_present(
        self,
        m_auto_attach,
        m_platform_info,
        m_get_licenses,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_get_licenses.return_value = ["unsupported-license"]
        m_platform_info.return_value = {"series": "ubuntu-lts"}
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 0
        assert m_get_licenses.call_count == 1

    @mock.patch("uaclient.jobs.gcp_auto_attach.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "get_licenses_from_identity")
    @mock.patch("uaclient.jobs.gcp_auto_attach.get_platform_info")
    @mock.patch("uaclient.jobs.gcp_auto_attach.action_auto_attach")
    def test_gcp_auto_attach_skips_non_lts(
        self,
        m_auto_attach,
        m_platform_info,
        m_get_licenses,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_platform_info.return_value = {"series": "ubuntu-non-lts"}
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 0
        assert m_get_licenses.call_count == 0

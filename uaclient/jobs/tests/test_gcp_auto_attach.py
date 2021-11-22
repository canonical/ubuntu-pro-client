import logging

import mock
import pytest

from uaclient.clouds.gcp import UAAutoAttachGCPInstance
from uaclient.exceptions import NonAutoAttachImageError
from uaclient.jobs.license_check import gcp_auto_attach


class TestGCPAutoAttachJob:
    @mock.patch("uaclient.jobs.license_check.get_cloud_type")
    @mock.patch("uaclient.jobs.license_check.action_auto_attach")
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
    @mock.patch("uaclient.jobs.license_check.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "is_license_present")
    @mock.patch.object(UAAutoAttachGCPInstance, "should_poll_for_license")
    @mock.patch("uaclient.jobs.license_check.action_auto_attach")
    def test_gcp_auto_attach(
        self,
        m_auto_attach,
        m_should_poll_for_license,
        m_is_license_present,
        m_cloud_type,
        cloud_type,
        caplog_text,
        FakeConfig,
    ):
        m_cloud_type.return_value = (cloud_type, None)
        m_should_poll_for_license.return_value = True
        m_is_license_present.return_value = True
        cfg = FakeConfig()

        m_auto_attach.return_value = 0
        return_value = gcp_auto_attach(cfg)

        if cloud_type != "gce":
            assert m_auto_attach.call_count == 0
            assert (
                "Disabling gcp_auto_attach job. Not running on GCP instance"
            ) in caplog_text()
            assert return_value is False

        else:
            assert m_auto_attach.call_count == 1
            assert return_value is True

    @mock.patch("uaclient.jobs.license_check.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "is_license_present")
    @mock.patch.object(UAAutoAttachGCPInstance, "should_poll_for_license")
    @mock.patch("uaclient.jobs.license_check.action_auto_attach")
    def test_gcp_job_dont_fail_if_non_auto_attach_image_error_is_raised(
        self,
        m_auto_attach,
        m_should_poll_for_license,
        m_is_license_present,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_should_poll_for_license.return_value = True
        m_is_license_present.return_value = True
        m_auto_attach.side_effect = NonAutoAttachImageError("error")
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 1

    @mock.patch("uaclient.jobs.license_check.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "is_license_present")
    @mock.patch.object(UAAutoAttachGCPInstance, "should_poll_for_license")
    @mock.patch("uaclient.jobs.license_check.action_auto_attach")
    def test_gcp_job_dont_fail_if_licenses_fail(
        self,
        m_auto_attach,
        m_should_poll_for_license,
        m_is_license_present,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_should_poll_for_license.return_value = True
        m_is_license_present.side_effect = TypeError("error")
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 0
        assert m_is_license_present.call_count == 1

    @mock.patch("uaclient.jobs.license_check.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "is_license_present")
    @mock.patch.object(UAAutoAttachGCPInstance, "should_poll_for_license")
    @mock.patch("uaclient.jobs.license_check.action_auto_attach")
    def test_gcp_auto_attach_license_not_present(
        self,
        m_auto_attach,
        m_should_poll_for_license,
        m_is_license_present,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_should_poll_for_license.return_value = True
        m_is_license_present.return_value = False
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 0
        assert m_is_license_present.call_count == 1

    @mock.patch("uaclient.jobs.license_check.get_cloud_type")
    @mock.patch.object(UAAutoAttachGCPInstance, "is_license_present")
    @mock.patch.object(UAAutoAttachGCPInstance, "should_poll_for_license")
    @mock.patch("uaclient.jobs.license_check.action_auto_attach")
    def test_gcp_auto_attach_skips_non_lts(
        self,
        m_auto_attach,
        m_should_poll_for_license,
        m_is_license_present,
        m_cloud_type,
        FakeConfig,
    ):
        m_cloud_type.return_value = ("gce", None)
        m_should_poll_for_license.return_value = False
        m_is_license_present.return_value = False
        cfg = FakeConfig()

        assert gcp_auto_attach(cfg) is False
        assert m_auto_attach.call_count == 0
        assert m_is_license_present.call_count == 0

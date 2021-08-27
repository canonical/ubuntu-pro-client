import mock
import pytest

from uaclient import exceptions, status
from uaclient.clouds.identity import (
    NoCloudTypeReason,
    cloud_instance_factory,
    get_cloud_type,
    get_instance_id,
)
from uaclient.util import ProcessExecutionError

M_PATH = "uaclient.clouds.identity."


class TestGetInstanceID:
    @mock.patch(M_PATH + "util.subp", return_value=("my-iid\n", ""))
    def test_use_cloud_init_query(self, m_subp):
        """Get instance_id from cloud-init query."""
        assert "my-iid" == get_instance_id()
        assert [
            mock.call(["cloud-init", "query", "instance_id"])
        ] == m_subp.call_args_list

    @mock.patch(
        M_PATH + "util.subp",
        side_effect=ProcessExecutionError("cloud-init query instance_id"),
    )
    def test_none_when_cloud_init_query_fails(self, m_subp):
        """Return None when cloud-init query fails."""
        assert None is get_instance_id()
        assert [
            mock.call(["cloud-init", "query", "instance_id"])
        ] == m_subp.call_args_list


class TestGetCloudType:
    @mock.patch(M_PATH + "util.which", return_value="/usr/bin/cloud-id")
    @mock.patch(M_PATH + "util.subp", return_value=("somecloud\n", ""))
    def test_use_cloud_id_when_available(self, m_subp, m_which):
        """Use cloud-id utility to discover cloud type."""
        assert ("somecloud", None) == get_cloud_type()
        assert [mock.call("cloud-id")] == m_which.call_args_list

    @mock.patch(M_PATH + "util.which", return_value="/usr/bin/cloud-id")
    @mock.patch(
        M_PATH + "util.subp", side_effect=ProcessExecutionError("cloud-id")
    )
    def test_error_when_cloud_id_fails(self, m_subp, m_which):
        assert (None, NoCloudTypeReason.CLOUD_ID_ERROR) == get_cloud_type()

    @pytest.mark.parametrize(
        "settings_overrides",
        (
            (
                """
                settings_overrides:
                  cloud_type: "azure"
                """
            ),
            (
                """
                settings_overrides:
                  other_setting: "blah"
                """
            ),
        ),
    )
    @mock.patch("uaclient.util.load_file")
    @mock.patch(M_PATH + "util.which", return_value="/usr/bin/cloud-id")
    @mock.patch(M_PATH + "util.subp", return_value=("test", ""))
    def test_cloud_type_when_using_settings_override(
        self, m_subp, m_which, m_load_file, settings_overrides
    ):
        if "azure" in settings_overrides:
            expected_value = "azure"
        else:
            expected_value = "test"

        m_load_file.return_value = settings_overrides
        assert get_cloud_type() == (expected_value, None)


@mock.patch(M_PATH + "get_cloud_type")
class TestCloudInstanceFactory:
    def test_raise_error_when_unable_to_get_cloud_type(self, m_get_cloud_type):
        """Raise appropriate error when unable to determine cloud_type."""
        m_get_cloud_type.return_value = (
            None,
            NoCloudTypeReason.NO_CLOUD_DETECTED,
        )
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cloud_instance_factory()
        assert 1 == m_get_cloud_type.call_count
        assert status.MESSAGE_UNABLE_TO_DETERMINE_CLOUD_TYPE == str(
            excinfo.value
        )

    def test_raise_error_when_not_aws_or_azure(self, m_get_cloud_type):
        """Raise appropriate error when unable to determine cloud_type."""
        m_get_cloud_type.return_value = ("unsupported-cloud", None)
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cloud_instance_factory()
        error_msg = status.MESSAGE_UNSUPPORTED_AUTO_ATTACH_CLOUD_TYPE.format(
            cloud_type="unsupported-cloud"
        )
        assert error_msg == str(excinfo.value)

    @pytest.mark.parametrize("cloud_type", ("aws", "azure"))
    def test_raise_error_when_not_viable_for_ubuntu_pro(
        self, m_get_cloud_type, cloud_type
    ):
        """Raise error when AWS or Azure instance is not viable auto-attach."""
        m_get_cloud_type.return_value = (cloud_type, None)

        def fake_invalid_instance():
            instance = mock.Mock()
            instance.is_viable = False
            return instance

        if cloud_type == "aws":
            M_INSTANCE_PATH = "uaclient.clouds.aws.UAAutoAttachAWSInstance"
        else:
            M_INSTANCE_PATH = "uaclient.clouds.azure.UAAutoAttachAzureInstance"

        with mock.patch(M_INSTANCE_PATH) as m_instance:
            m_instance.side_effect = fake_invalid_instance
            with pytest.raises(exceptions.UserFacingError) as excinfo:
                cloud_instance_factory()
        error_msg = status.MESSAGE_UNSUPPORTED_AUTO_ATTACH
        assert error_msg == str(excinfo.value)

    @pytest.mark.parametrize(
        "cloud_type", ("aws", "aws-gov", "aws-china", "azure")
    )
    def test_return_cloud_instance_on_viable_clouds(
        self, m_get_cloud_type, cloud_type
    ):
        """Return UAAutoAttachInstance when matching cloud_type is viable."""
        m_get_cloud_type.return_value = (cloud_type, None)

        fake_instance = mock.Mock()
        fake_instance.is_viable = True

        def fake_viable_instance():
            return fake_instance

        if cloud_type == "azure":
            M_INSTANCE_PATH = "uaclient.clouds.azure.UAAutoAttachAzureInstance"
        else:
            M_INSTANCE_PATH = "uaclient.clouds.aws.UAAutoAttachAWSInstance"

        with mock.patch(M_INSTANCE_PATH) as m_instance:
            m_instance.side_effect = fake_viable_instance
            assert fake_instance == cloud_instance_factory()

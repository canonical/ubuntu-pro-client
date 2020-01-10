import json
import mock

import pytest

from uaclient.clouds.identity import (
    cloud_instance_factory,
    get_cloud_type,
    get_cloud_type_from_result_file,
)
from uaclient import exceptions
from uaclient import status

M_PATH = "uaclient.clouds.identity."


class TestGetCloudTypeFromResultFile:
    @pytest.mark.parametrize(
        "ds_name,expected",
        (
            ("DataSourceSomeTHING", "something"),
            ("DaTaSoUrCeMiNe", "mine"),
            ("DataSourceEc2", "aws"),
            ("DataSourceEc2Lookalike", "ec2lookalike"),
        ),
    )
    def test_get_cloud_type_from_lowercase_v1_datasource_key(
        self, ds_name, expected, tmpdir
    ):
        """The value of cloud_type is extracted from results datasource key.

        ec2 gets mapped to aws"""
        results = {"v1": {"datasource": ds_name}}
        result_file = tmpdir.join("result.json")
        result_file.write(json.dumps(results))
        cloud_type = get_cloud_type_from_result_file(result_file.strpath)
        assert cloud_type == expected


class TestGetCloudType:
    @mock.patch(M_PATH + "util.which", return_value="/usr/bin/cloud-id")
    @mock.patch(M_PATH + "util.subp", return_value=("somecloud\n", ""))
    def test_use_cloud_id_when_available(self, m_subp, m_which):
        """Use cloud-id utility to discover cloud type."""
        assert "somecloud" == get_cloud_type()
        assert [mock.call("cloud-id")] == m_which.call_args_list

    @mock.patch(
        M_PATH + "get_cloud_type_from_result_file", return_value="cloud9"
    )
    @mock.patch(M_PATH + "util.which", return_value=None)
    def test_fallback_to_get_cloud_type_from_result_file(
        self, m_subp, m_cloud_type_from_result_file
    ):
        """Use cloud-id utility to discover cloud type."""
        assert "cloud9" == get_cloud_type()
        assert [mock.call()] == m_cloud_type_from_result_file.call_args_list

    @mock.patch(M_PATH + "util.which", return_value=None)
    @mock.patch(
        M_PATH + "get_cloud_type_from_result_file",
        side_effect=FileNotFoundError,
    )
    def test_fallback_if_no_cloud_type_found(
        self, m_cloud_type_from_result_file, m_which
    ):
        assert get_cloud_type() is None


@mock.patch(M_PATH + "get_cloud_type")
class TestCloudInstanceFactory:
    def test_raise_error_when_unable_to_get_cloud_type(self, m_get_cloud_type):
        """Raise appropriate error when unable to determine cloud_type."""
        m_get_cloud_type.return_value = None
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cloud_instance_factory()
        assert 1 == m_get_cloud_type.call_count
        assert status.MESSAGE_UNABLE_TO_DETERMINE_CLOUD_TYPE == str(
            excinfo.value
        )

    def test_raise_error_when_not_aws_or_azure(self, m_get_cloud_type):
        """Raise appropriate error when unable to determine cloud_type."""
        m_get_cloud_type.return_value = "unsupported-cloud"
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
        m_get_cloud_type.return_value = cloud_type

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

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

    def test_raise_error_when_not_aws(self, m_get_cloud_type):
        """Raise appropriate error when unable to determine cloud_type."""
        m_get_cloud_type.return_value = "nonaws"
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cloud_instance_factory()
        error_msg = status.MESSAGE_UNSUPPORTED_PREMIUM_CLOUD_TYPE.format(
            cloud_type="nonaws"
        )
        assert error_msg == str(excinfo.value)

    @mock.patch("uaclient.clouds.aws.UAPremiumAWSInstance")
    def test_raise_error_when_not_viable_aws_premium(
        self, m_aws_instance, m_get_cloud_type
    ):
        """Raise appropriate error when the AWS instance is not viable."""
        m_get_cloud_type.return_value = "aws"

        def fake_aws_instance():
            instance = mock.Mock()
            instance.is_viable = False
            return instance

        m_aws_instance.side_effect = fake_aws_instance
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cloud_instance_factory()
        error_msg = status.MESSAGE_UNSUPPORTED_PREMIUM
        assert error_msg == str(excinfo.value)

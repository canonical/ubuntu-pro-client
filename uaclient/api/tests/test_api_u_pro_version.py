import mock
import pytest

from uaclient.api.u.pro.version.v1 import VersionError, VersionResult, version
from uaclient.exceptions import UserFacingError


class TestVersionV1:
    @mock.patch("uaclient.api.u.pro.version.v1.get_version", return_value="28")
    def test_version(self, _m_get_version):
        result = version()
        assert isinstance(result, VersionResult)
        assert result.installed_version == "28"

    @mock.patch("uaclient.api.u.pro.version.v1.get_version")
    def test_version_error(self, m_get_version):
        m_get_version.side_effect = UserFacingError(
            "something wrong", "fn-specific"
        )

        with pytest.raises(VersionError) as excinfo:
            version()

        assert excinfo.errisinstance(VersionError)
        assert excinfo.value.msg == "('something wrong', 'fn-specific')"
        assert excinfo.value.msg_code == "unable-to-determine-version"

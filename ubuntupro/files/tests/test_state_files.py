import pytest

from uaclient.files.state_files import _services_once_enable_preprocess_data


class TestServicesOnceEnabledPreprocessData:
    @pytest.mark.parametrize(
        "content",
        (
            ({"fips-updates": True}),
            ({"fips_updates": True}),
        ),
    )
    def test_add_service(self, content):
        assert _services_once_enable_preprocess_data(content) == {
            "fips_updates": True
        }

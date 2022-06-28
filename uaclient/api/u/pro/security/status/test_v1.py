import mock

from uaclient.api.u.pro.security.status.v1 import status

M_PATH = "uaclient.api.u.pro.security.status.v1."


class TestApiUProSecurityStatusV1:
    @mock.patch(
        M_PATH + "get_service_name",
        return_value=("esm-infra", "some.url.for.esm"),
    )
    @mock.patch(
        M_PATH + "filter_security_updates", return_value=[mock.MagicMock()] * 2
    )
    @mock.patch(M_PATH + "get_origin_for_package", return_value="main")
    @mock.patch(
        M_PATH + "get_installed_packages", return_value=[mock.MagicMock()] * 10
    )
    @mock.patch(
        M_PATH + "get_ua_info",
        return_value={
            "attached": False,
            "enabled_services": [],
            "entitled_services": [],
        },
    )
    def test_security_status_format(
        self,
        _m_get_ua_info,
        _m_get_installed_packages,
        _m_get_origin_for_package,
        _m_filter_security_updates,
        _m_get_service_name,
    ):
        expected_output = {
            "_schema_version": "0.1",
            "packages": [
                {
                    "package": mock.ANY,
                    "version": mock.ANY,
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                },
                {
                    "package": mock.ANY,
                    "version": mock.ANY,
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                },
            ],
            "summary": {
                "ua": {
                    "attached": False,
                    "enabled_services": [],
                    "entitled_services": [],
                },
                "num_installed_packages": 10,
                "num_main_packages": 10,
                "num_restricted_packages": 0,
                "num_universe_packages": 0,
                "num_multiverse_packages": 0,
                "num_third_party_packages": 0,
                "num_unknown_packages": 0,
                "num_esm_infra_packages": 0,
                "num_esm_apps_packages": 0,
                "num_esm_infra_updates": 2,
                "num_esm_apps_updates": 0,
                "num_standard_security_updates": 0,
            },
        }

        assert expected_output == status().to_dict()

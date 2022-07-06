import mock

from uaclient.api.u.pro.security.status import v1
from uaclient.api.u.pro.security.status.v2 import status

M_PATH = "uaclient.api.u.pro.security.status.v2."


class TestApiUProSecurityStatusV1:
    @mock.patch(
        M_PATH + "v1.status",
        return_value=v1.SecurityStatusResult.from_dict(
            {
                "_schema_version": "0.1",
                "packages": [
                    {
                        "package": "any",
                        "version": "any",
                        "service_name": "esm-infra",
                        "status": "pending_attach",
                        "origin": "some.url.for.esm",
                        "download_size": 123456,
                    },
                    {
                        "package": "any",
                        "version": "any",
                        "service_name": "esm-infra",
                        "status": "pending_attach",
                        "origin": "some.url.for.esm",
                        "download_size": 123456,
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
        ),
    )
    def test_security_status_format(
        self,
        _m_v1_status,
    ):
        expected_output = {
            "updates": [
                {
                    "package": mock.ANY,
                    "version": mock.ANY,
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                    "download_size": mock.ANY,
                },
                {
                    "package": mock.ANY,
                    "version": mock.ANY,
                    "service_name": "esm-infra",
                    "status": "pending_attach",
                    "origin": "some.url.for.esm",
                    "download_size": mock.ANY,
                },
            ],
            "summary": {
                "pro": {
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

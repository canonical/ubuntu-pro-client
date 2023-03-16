import logging
from io import BytesIO
from urllib.error import HTTPError

import mock
import pytest

from uaclient import system
from uaclient.clouds.gcp import (
    LAST_ETAG,
    LICENSES_URL,
    TOKEN_URL,
    WAIT_FOR_CHANGE,
    UAAutoAttachGCPInstance,
)
from uaclient.exceptions import GCPProAccountError

M_PATH = "uaclient.clouds.gcp."


class TestUAAutoAttachGCPInstance:
    def test_cloud_type(self):
        """cloud_type is returned as GCP."""
        instance = UAAutoAttachGCPInstance()
        assert "gcp" == instance.cloud_type

    @mock.patch(M_PATH + "util.readurl")
    def test_identity_doc_from_gcp_url(self, readurl):
        """Return attested signature and compute info as GCP identity doc"""
        readurl.return_value = "attestedWOOT!===", {"header": "stuff"}
        instance = UAAutoAttachGCPInstance()
        assert {"identityToken": "attestedWOOT!==="} == instance.identity_doc
        assert [
            mock.call(
                TOKEN_URL, headers={"Metadata-Flavor": "Google"}, timeout=1
            )
        ] == readurl.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("fail_count,exception", ((3, False), (4, True)))
    @mock.patch(M_PATH + "util.time.sleep")
    @mock.patch(M_PATH + "util.readurl")
    def test_retry_backoff_on_failed_identity_doc(
        self, readurl, sleep, fail_count, exception, caplog_text
    ):
        """Retries backoff before failing to get GCP.identity_doc"""

        def fake_someurlerrors(url, headers, timeout):
            if readurl.call_count <= fail_count:
                raise HTTPError(
                    "http://me",
                    700 + readurl.call_count,
                    "funky error msg",
                    None,
                    BytesIO(),
                )

            return "attestedWOOT!===", {"header": "stuff"}

        readurl.side_effect = fake_someurlerrors

        instance = UAAutoAttachGCPInstance()
        if exception:
            with pytest.raises(GCPProAccountError) as excinfo:
                instance.identity_doc
            assert 704 == excinfo.value.code
        else:
            assert {
                "identityToken": "attestedWOOT!==="
            } == instance.identity_doc

        expected_sleep_calls = [mock.call(0.5), mock.call(1), mock.call(1)]
        assert expected_sleep_calls == sleep.call_args_list

        expected_logs = [
            "GCPProServiceAccount Error 701: "
            + "funky error msg Retrying 3 more times.",
            "GCPProServiceAccount Error 702: "
            + "funky error msg Retrying 2 more times.",
            "GCPProServiceAccount Error 703: "
            + "funky error msg Retrying 1 more times.",
        ]
        logs = caplog_text()
        for log in expected_logs:
            assert log in logs

    @pytest.mark.parametrize(
        "product_name,viable",
        (
            (None, False),
            ("Google Compute Engine", True),
            ("CoolCloudCorp", False),
        ),
    )
    @mock.patch(M_PATH + "os.path.exists")
    @mock.patch(M_PATH + "system.load_file")
    def test_is_viable_based_on_dmi_product_name(
        self, load_file, m_exists, product_name, viable
    ):
        """Platform viable if product name matches."""

        def fake_exists(f_name):
            if f_name == "/sys/class/dmi/id/product_name":
                return bool(product_name is not None)
            raise AssertionError("Invalid os.path.exist of {}".format(f_name))

        m_exists.side_effect = fake_exists

        def fake_load_file(f_name):
            if f_name == "/sys/class/dmi/id/product_name":
                return product_name
            raise AssertionError("Invalid load_file of {}".format(f_name))

        load_file.side_effect = fake_load_file

        instance = UAAutoAttachGCPInstance()
        assert viable is instance.is_viable

    @pytest.mark.parametrize(
        "existing_etag, wait_for_change, metadata_response, platform_info,"
        " expected_etag, expected_result, expected_readurl",
        (
            (
                None,
                False,
                ([], {}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="xenial",
                    pretty_version="",
                ),
                None,
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                None,
                False,
                ([{"id": "8045211386737108299"}], {}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="xenial",
                    pretty_version="",
                ),
                None,
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                None,
                False,
                ([{"id": "8045211386737108299"}], {}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="bionic",
                    pretty_version="",
                ),
                None,
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                None,
                False,
                ([{"id": "6022427724719891830"}], {}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="bionic",
                    pretty_version="",
                ),
                None,
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                None,
                False,
                ([{"id": "599959289349842382"}], {}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="focal",
                    pretty_version="",
                ),
                None,
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                None,
                False,
                ([{"id": "8045211386737108299"}], {"ETag": "test-etag"}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="xenial",
                    pretty_version="",
                ),
                "test-etag",
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                None,
                False,
                ([{"id": "wrong"}], {"ETag": "test-etag"}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="xenial",
                    pretty_version="",
                ),
                "test-etag",
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                None,
                True,
                ([{"id": "8045211386737108299"}], {"ETag": "test-etag"}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="xenial",
                    pretty_version="",
                ),
                "test-etag",
                True,
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    )
                ],
            ),
            (
                "existing-etag",
                True,
                ([{"id": "8045211386737108299"}], {"ETag": "test-etag"}),
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="xenial",
                    pretty_version="",
                ),
                "test-etag",
                True,
                [
                    mock.call(
                        LICENSES_URL
                        + WAIT_FOR_CHANGE
                        + LAST_ETAG.format(etag="existing-etag"),
                        headers={"Metadata-Flavor": "Google"},
                    )
                ],
            ),
        ),
    )
    @mock.patch(M_PATH + "system.get_release_info")
    @mock.patch(M_PATH + "util.readurl")
    def test_is_license_present(
        self,
        m_readurl,
        m_get_release_info,
        existing_etag,
        wait_for_change,
        metadata_response,
        platform_info,
        expected_etag,
        expected_result,
        expected_readurl,
    ):
        instance = UAAutoAttachGCPInstance()
        instance.etag = existing_etag
        m_readurl.return_value = metadata_response
        m_get_release_info.return_value = platform_info

        result = instance.is_pro_license_present(
            wait_for_change=wait_for_change
        )

        assert expected_result == result
        assert expected_etag == instance.etag

        assert expected_readurl == m_readurl.call_args_list

    @pytest.mark.parametrize(
        "platform_info, expected_result",
        (
            (
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="xenial",
                    pretty_version="",
                ),
                True,
            ),
            (
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="bionic",
                    pretty_version="",
                ),
                True,
            ),
            (
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="focal",
                    pretty_version="",
                ),
                True,
            ),
            (
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="non_lts",
                    pretty_version="",
                ),
                False,
            ),
            (
                system.ReleaseInfo(
                    distribution="",
                    release="",
                    series="jammy",
                    pretty_version="",
                ),
                True,
            ),
        ),
    )
    @mock.patch(M_PATH + "system.get_release_info")
    def test_should_poll_for_license(
        self, m_get_release_info, platform_info, expected_result
    ):
        m_get_release_info.return_value = platform_info
        instance = UAAutoAttachGCPInstance()
        result = instance.should_poll_for_pro_license()
        assert expected_result == result

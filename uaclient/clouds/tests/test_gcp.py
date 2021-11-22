import logging
from io import BytesIO
from urllib.error import HTTPError

import mock
import pytest

from uaclient.clouds.gcp import (
    LAST_ETAG,
    LICENSES_URL,
    TOKEN_URL,
    WAIT_FOR_CHANGE,
    UAAutoAttachGCPInstance,
)

M_PATH = "uaclient.clouds.gcp."


class TestUAAutoAttachGCPInstance:
    def test_cloud_type(self, FakeConfig):
        """cloud_type is returned as GCP."""
        instance = UAAutoAttachGCPInstance(FakeConfig())
        assert "gcp" == instance.cloud_type

    @mock.patch(M_PATH + "util.readurl")
    def test_identity_doc_from_gcp_url(self, readurl, FakeConfig):
        """Return attested signature and compute info as GCP identity doc"""
        readurl.return_value = "attestedWOOT!===", {"header": "stuff"}
        instance = UAAutoAttachGCPInstance(FakeConfig())
        assert {"identityToken": "attestedWOOT!==="} == instance.identity_doc
        assert [
            mock.call(TOKEN_URL, headers={"Metadata-Flavor": "Google"})
        ] == readurl.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("fail_count,exception", ((3, False), (4, True)))
    @mock.patch(M_PATH + "util.time.sleep")
    @mock.patch(M_PATH + "util.readurl")
    def test_retry_backoff_on_failed_identity_doc(
        self, readurl, sleep, fail_count, exception, caplog_text, FakeConfig
    ):
        """Retries backoff before failing to get GCP.identity_doc"""

        def fake_someurlerrors(url, headers):
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

        instance = UAAutoAttachGCPInstance(FakeConfig())
        if exception:
            with pytest.raises(HTTPError) as excinfo:
                instance.identity_doc
            assert 704 == excinfo.value.code
        else:
            assert {
                "identityToken": "attestedWOOT!==="
            } == instance.identity_doc

        expected_sleep_calls = [mock.call(1), mock.call(2), mock.call(5)]
        assert expected_sleep_calls == sleep.call_args_list

        expected_logs = [
            "HTTP Error 701: funky error msg Retrying 3 more times.",
            "HTTP Error 702: funky error msg Retrying 2 more times.",
            "HTTP Error 703: funky error msg Retrying 1 more times.",
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
    @mock.patch(M_PATH + "util.load_file")
    def test_is_viable_based_on_dmi_product_name(
        self, load_file, m_exists, product_name, viable, FakeConfig
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

        instance = UAAutoAttachGCPInstance(FakeConfig())
        assert viable is instance.is_viable

    @pytest.mark.parametrize(
        "metadata_response, platform_info, expected_etag, expected_result,"
        " expected_readurl",
        (
            (
                ([], {}),
                {"series": "xenial"},
                None,
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                ([], {}),
                {"series": "bionic"},
                None,
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                ([], {}),
                {"series": "focal"},
                None,
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (([], {}), {"series": "impish"}, None, False, []),
            (([], {}), {"series": "jammy"}, None, False, []),
            (
                ([{"id": "8045211386737108299"}], {}),
                {"series": "xenial"},
                None,
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                ([{"id": "8045211386737108299"}], {}),
                {"series": "bionic"},
                None,
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                ([{"id": "6022427724719891830"}], {}),
                {"series": "bionic"},
                None,
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                ([{"id": "599959289349842382"}], {}),
                {"series": "focal"},
                None,
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                ([{"id": "8045211386737108299"}], {"ETag": "test-etag"}),
                {"series": "xenial"},
                "test-etag",
                True,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
            (
                ([{"id": "wrong"}], {"ETag": "test-etag"}),
                {"series": "xenial"},
                "test-etag",
                False,
                [
                    mock.call(
                        LICENSES_URL, headers={"Metadata-Flavor": "Google"}
                    )
                ],
            ),
        ),
    )
    @mock.patch(M_PATH + "util.get_platform_info")
    @mock.patch(M_PATH + "util.readurl")
    def test_is_license_present(
        self,
        m_readurl,
        m_get_platform_info,
        metadata_response,
        platform_info,
        expected_etag,
        expected_result,
        expected_readurl,
        FakeConfig,
    ):
        m_readurl.return_value = metadata_response
        m_get_platform_info.return_value = platform_info
        instance = UAAutoAttachGCPInstance(FakeConfig())
        instance.etag = None

        result = instance.is_license_present()

        assert expected_result == result
        assert expected_etag == instance.etag

        assert expected_readurl == m_readurl.call_args_list

    @pytest.mark.parametrize(
        "platform_info, expected_result",
        (
            ({"series": "xenial"}, True),
            ({"series": "bionic"}, True),
            ({"series": "focal"}, True),
            ({"series": "impish"}, False),
            ({"series": "jammy"}, False),
        ),
    )
    @mock.patch(M_PATH + "util.get_platform_info")
    def test_should_poll_for_license(
        self, m_get_platform_info, platform_info, expected_result, FakeConfig
    ):
        m_get_platform_info.return_value = platform_info
        instance = UAAutoAttachGCPInstance(FakeConfig())
        result = instance.should_poll_for_license()
        assert expected_result == result

    @pytest.mark.parametrize(
        "metadata_responses, platform_info, expected_readurl,"
        "expected_auto_attach_call_count, expected_sleep_call_count",
        (
            (
                [([{"id": "8045211386737108299"}], {})],
                {"series": "xenial"},
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    )
                ],
                1,
                0,
            ),
            (
                [([{"id": "6022427724719891830"}], {})],
                {"series": "bionic"},
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    )
                ],
                1,
                0,
            ),
            (
                [([{"id": "599959289349842382"}], {})],
                {"series": "focal"},
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    )
                ],
                1,
                0,
            ),
            (
                [
                    ([], {"ETag": "tag1"}),
                    ([], {"ETag": "tag2"}),
                    ([{"id": "8045211386737108299"}], {}),
                ],
                {"series": "xenial"},
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    ),
                    mock.call(
                        LICENSES_URL
                        + WAIT_FOR_CHANGE
                        + LAST_ETAG.format("tag1"),
                        headers={"Metadata-Flavor": "Google"},
                    ),
                    mock.call(
                        LICENSES_URL
                        + WAIT_FOR_CHANGE
                        + LAST_ETAG.format("tag2"),
                        headers={"Metadata-Flavor": "Google"},
                    ),
                ],
                1,
                0,
            ),
            (
                [
                    HTTPError("", 400, "", None, None),
                    ([{"id": "8045211386737108299"}], {}),
                ],
                {"series": "xenial"},
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    )
                ],
                0,
                0,
            ),
            (
                [
                    HTTPError("", 500, "", None, None),
                    ([{"id": "8045211386737108299"}], {}),
                ],
                {"series": "xenial"},
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    ),
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    ),
                ],
                1,
                1,
            ),
            (
                [
                    Exception(),
                    Exception(),
                    ([{"id": "8045211386737108299"}], {}),
                ],
                {"series": "xenial"},
                [
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    ),
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    ),
                    mock.call(
                        LICENSES_URL + WAIT_FOR_CHANGE,
                        headers={"Metadata-Flavor": "Google"},
                    ),
                ],
                1,
                2,
            ),
        ),
    )
    @mock.patch(M_PATH + "time.sleep")
    @mock.patch(M_PATH + "lock.SpinLock.__exit__")
    @mock.patch(M_PATH + "lock.SpinLock.__enter__")
    @mock.patch(M_PATH + "actions.auto_attach")
    @mock.patch(M_PATH + "util.get_platform_info")
    @mock.patch(M_PATH + "util.readurl")
    def test_gcp_polling_fn_auto_attaches_when_license_found(
        self,
        m_readurl,
        m_get_platform_info,
        m_auto_attach,
        _m_lock_enter,
        _m_lock_exit,
        m_sleep,
        metadata_responses,
        platform_info,
        expected_readurl,
        expected_auto_attach_call_count,
        expected_sleep_call_count,
        FakeConfig,
    ):
        m_readurl.side_effect = metadata_responses
        m_get_platform_info.return_value = platform_info
        instance = UAAutoAttachGCPInstance(FakeConfig())
        instance.etag = None

        gcp_polling_fn = instance.get_polling_fn()

        assert gcp_polling_fn is not None

        gcp_polling_fn()

        assert expected_readurl == m_readurl.call_args_list
        assert expected_auto_attach_call_count == m_auto_attach.call_count
        assert expected_sleep_call_count == m_sleep.call_count

import logging
from io import BytesIO
from urllib.error import HTTPError

import mock
import pytest

from uaclient.clouds.gcp import TOKEN_URL, UAAutoAttachGCPInstance

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
            mock.call(TOKEN_URL, headers={"Metadata-Flavor": "Google"})
        ] == readurl.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("fail_count,exception", ((3, False), (4, True)))
    @mock.patch(M_PATH + "util.time.sleep")
    @mock.patch(M_PATH + "util.readurl")
    def test_retry_backoff_on_failed_identity_doc(
        self, readurl, sleep, fail_count, exception, caplog_text
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

        instance = UAAutoAttachGCPInstance()
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

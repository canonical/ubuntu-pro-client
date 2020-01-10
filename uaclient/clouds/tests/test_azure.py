import logging
import mock
from io import BytesIO
from urllib.error import HTTPError

import pytest

from uaclient.clouds.azure import IMDS_BASE_URL, UAAutoAttachAzureInstance

M_PATH = "uaclient.clouds.azure."


class TestUAAutoAttachAzureInstance:
    def test_cloud_type(self):
        """cloud_type is returned as azure."""
        instance = UAAutoAttachAzureInstance()
        assert "azure" == instance.cloud_type

    @mock.patch(M_PATH + "util.readurl")
    def test_identity_doc_from_azure_url_pkcs7(self, readurl):
        """Return attested signature and compute info as Azure identity doc"""

        def fake_readurl(url, headers):
            if "attested/document" in url:
                return {"signature": "attestedWOOT!==="}, {"header": "stuff"}
            elif "instance/compute" in url:
                return {"computekey": "computeval"}, {"header": "stuff"}
            else:
                raise AssertionError("Unexpected URL provided %s" % url)

        readurl.side_effect = fake_readurl
        instance = UAAutoAttachAzureInstance()
        assert {
            "compute": {"computekey": "computeval"},
            "pkcs7": "attestedWOOT!===",
        } == instance.identity_doc
        url1 = IMDS_BASE_URL + "instance/compute?api-version=2019-06-04"
        url2 = IMDS_BASE_URL + "attested/document?api-version=2019-06-04"
        assert [
            mock.call(url1, headers={"Metadata": "true"}),
            mock.call(url2, headers={"Metadata": "true"}),
        ] == readurl.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("fail_count,exception", ((3, False), (4, True)))
    @mock.patch(M_PATH + "util.time.sleep")
    @mock.patch(M_PATH + "util.readurl")
    def test_retry_backoff_on_failed_identity_doc(
        self, readurl, sleep, fail_count, exception, caplog_text
    ):
        """Retries backoff before failing to get Azure.identity_doc"""

        def fake_someurlerrors(url, headers):
            if readurl.call_count <= fail_count:
                raise HTTPError(
                    "http://me",
                    700 + readurl.call_count,
                    "funky error msg",
                    None,
                    BytesIO(),
                )
            if "attested" in url:
                return {"signature": "attestedWOOT!==="}, {"header": "stuff"}
            elif "compute" in url:
                return {"computekey": "computeval"}, {"header": "stuff"}
            raise AssertionError("Unexpected url requested {}".format(url))

        readurl.side_effect = fake_someurlerrors
        instance = UAAutoAttachAzureInstance()
        if exception:
            with pytest.raises(HTTPError) as excinfo:
                instance.identity_doc
            assert 704 == excinfo.value.code
        else:
            assert {
                "pkcs7": "attestedWOOT!===",
                "compute": {"computekey": "computeval"},
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
        "chassis_asset_tag,ovf_env_exists,viable",
        (
            (None, True, True),
            ("7783-7084-3265-9085-8269-3286-77", False, True),
            ("6783-7084-3265-9085-8269-3286-77", True, True),
            (None, False, False),
            ("6783-7084-3265-9085-8269-3286-77", False, False),
        ),
    )
    @mock.patch(M_PATH + "os.path.exists")
    @mock.patch(M_PATH + "util.load_file")
    def test_is_viable_based_on_dmi_chassis_asset_tag_or_ovf_env(
        self, load_file, m_exists, chassis_asset_tag, ovf_env_exists, viable
    ):
        """Platform viable if chassis asset tag matches or ovf.env exists."""

        def fake_exists(f_name):
            if f_name == "/sys/class/dmi/id/chassis_asset_tag":
                return bool(chassis_asset_tag is not None)
            elif f_name == "/var/lib/cloud/seed/azure/ovf-env.xml":
                return ovf_env_exists
            raise AssertionError("Invalid os.path.exist of {}".format(f_name))

        m_exists.side_effect = fake_exists

        def fake_load_file(f_name):
            if f_name == "/sys/class/dmi/id/chassis_asset_tag":
                return chassis_asset_tag
            raise AssertionError("Invalid load_file of {}".format(f_name))

        load_file.side_effect = fake_load_file
        instance = UAAutoAttachAzureInstance()
        assert viable is instance.is_viable

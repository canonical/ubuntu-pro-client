import logging
import re

import mock
import pytest

from uaclient import exceptions, http
from uaclient.clouds.aws import (
    AWS_TOKEN_PUT_HEADER,
    AWS_TOKEN_REQ_HEADER,
    AWS_TOKEN_TTL_SECONDS,
    IMDS_IPV4_ADDRESS,
    IMDS_IPV6_ADDRESS,
    IMDS_URL,
    IMDS_V2_TOKEN_URL,
    UAAutoAttachAWSInstance,
)

M_PATH = "uaclient.clouds.aws."


class TestUAAutoAttachAWSInstance:
    def test_cloud_type(self):
        instance = UAAutoAttachAWSInstance()
        assert "aws" == instance.cloud_type

    @mock.patch(M_PATH + "http.readurl")
    def test__get_imds_v2_token_headers_none_on_404(self, readurl):
        """A 404 on private AWS regions indicates lack IMDSv2 support."""
        readurl.return_value = http.HTTPResponse(
            code=404,
            headers={},
            body="",
            json_dict={},
            json_list=[],
        )
        instance = UAAutoAttachAWSInstance()
        assert None is instance._get_imds_v2_token_headers(
            ip_address=IMDS_IPV4_ADDRESS
        )
        assert "IMDSv1" == instance._api_token
        # No retries on 404. It is a permanent indication of no IMDSv2 support.
        instance._get_imds_v2_token_headers(ip_address=IMDS_IPV4_ADDRESS)
        assert 1 == readurl.call_count

    @mock.patch(M_PATH + "http.readurl")
    def test__get_imds_v2_token_headers_caches_response(self, readurl):
        """Return API token headers for IMDSv2 access. Response is cached."""
        instance = UAAutoAttachAWSInstance()
        url = "http://169.254.169.254/latest/api/token"
        readurl.return_value = http.HTTPResponse(
            code=200,
            headers={"header": "stuff"},
            body="somebase64token==",
            json_dict={},
            json_list=[],
        )
        assert {
            AWS_TOKEN_PUT_HEADER: "somebase64token=="
        } == instance._get_imds_v2_token_headers(ip_address=IMDS_IPV4_ADDRESS)
        instance._get_imds_v2_token_headers(ip_address=IMDS_IPV4_ADDRESS)
        assert "somebase64token==" == instance._api_token
        assert [
            mock.call(
                url,
                method="PUT",
                headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
                timeout=1,
            )
        ] == readurl.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("fail_count,exception", ((3, False), (4, True)))
    @mock.patch(M_PATH + "util.time.sleep")
    @mock.patch(M_PATH + "http.readurl")
    def test_retry_backoff_on__get_imds_v2_token_headers_caches_response(
        self, readurl, sleep, fail_count, exception, caplog_text
    ):
        """Retry backoff before failing _get_imds_v2_token_headers."""

        def fake_someurlerrors(url, method=None, headers=None, timeout=1):
            if readurl.call_count <= fail_count:
                return http.HTTPResponse(
                    code=700 + readurl.call_count,
                    headers={},
                    body="funky error msg",
                    json_dict={},
                    json_list=[],
                )
            return http.HTTPResponse(
                code=200,
                headers={"header": "stuff"},
                body="base64token==",
                json_dict={},
                json_list=[],
            )

        readurl.side_effect = fake_someurlerrors
        instance = UAAutoAttachAWSInstance()
        if exception:
            with pytest.raises(exceptions.CloudMetadataError):
                instance._get_imds_v2_token_headers(
                    ip_address=IMDS_IPV4_ADDRESS
                )
        else:
            assert {
                AWS_TOKEN_PUT_HEADER: "base64token=="
            } == instance._get_imds_v2_token_headers(
                ip_address=IMDS_IPV4_ADDRESS
            )

        expected_sleep_calls = [mock.call(1), mock.call(2), mock.call(5)]
        assert expected_sleep_calls == sleep.call_args_list
        expected_logs = [
            "An error occurred while talking the the cloud metadata service: 701 - funky error msg: Retrying 3 more times.",  # noqa: E501
            "An error occurred while talking the the cloud metadata service: 702 - funky error msg: Retrying 2 more times.",  # noqa: E501
            "An error occurred while talking the the cloud metadata service: 703 - funky error msg: Retrying 1 more times.",  # noqa: E501
        ]
        logs = caplog_text()
        for log in expected_logs:
            assert log in logs

    @mock.patch(M_PATH + "http.readurl")
    def test_identity_doc_from_aws_url_pkcs7(self, readurl):
        """Return pkcs7 content from IMDS as AWS' identity doc"""
        readurl.return_value = http.HTTPResponse(
            code=200,
            headers={"header": "stuff"},
            body="pkcs7WOOT!==",
            json_dict={},
            json_list=[],
        )
        instance = UAAutoAttachAWSInstance()
        assert {"pkcs7": "pkcs7WOOT!=="} == instance.identity_doc
        url = "http://169.254.169.254/latest/dynamic/instance-identity/pkcs7"
        token_url = "http://169.254.169.254/latest/api/token"
        assert [
            mock.call(
                token_url,
                method="PUT",
                headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
                timeout=1,
            ),
            mock.call(
                url, headers={AWS_TOKEN_PUT_HEADER: "pkcs7WOOT!=="}, timeout=1
            ),
        ] == readurl.call_args_list

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize("fail_count,exception", ((3, False),))
    @mock.patch(M_PATH + "util.time.sleep")
    @mock.patch(M_PATH + "http.readurl")
    def test_retry_backoff_on_failed_identity_doc(
        self, readurl, sleep, fail_count, exception, caplog_text
    ):
        """Retry backoff is attempted before failing to get AWS.identity_doc"""

        def fake_someurlerrors(url, method=None, headers=None, timeout=1):
            # due to _get_imds_v2_token_headers
            if "latest/api/token" in url:
                return http.HTTPResponse(
                    code=200,
                    headers={"header": "stuff"},
                    body="base64token==",
                    json_dict={},
                    json_list=[],
                )
            if readurl.call_count <= fail_count + 1:
                return http.HTTPResponse(
                    code=700 + readurl.call_count,
                    headers={},
                    body="funky error msg",
                    json_dict={},
                    json_list=[],
                )
            return http.HTTPResponse(
                code=200,
                headers={"header": "stuff"},
                body="pkcs7WOOT!==",
                json_dict={},
                json_list=[],
            )

        readurl.side_effect = fake_someurlerrors
        instance = UAAutoAttachAWSInstance()
        if exception:
            with pytest.raises(exceptions.CloudMetadataError) as excinfo:
                instance.identity_doc
            assert 705 == excinfo.value.code
        else:
            assert {"pkcs7": "pkcs7WOOT!=="} == instance.identity_doc

        expected_sleep_calls = [mock.call(0.5), mock.call(1), mock.call(1)]
        assert expected_sleep_calls == sleep.call_args_list
        expected_logs = [
            "An error occurred while talking the the cloud metadata service: 702 - funky error msg: Retrying 3 more times.",  # noqa: E501
            "An error occurred while talking the the cloud metadata service: 703 - funky error msg: Retrying 2 more times.",  # noqa: E501
            "An error occurred while talking the the cloud metadata service: 704 - funky error msg: Retrying 1 more times.",  # noqa: E501
        ]
        logs = caplog_text()
        for log in expected_logs:
            assert log in logs

    @pytest.mark.parametrize("uuid", ("ec2", "ec2yep"))
    @mock.patch(M_PATH + "system.load_file")
    def test_is_viable_based_on_sys_hypervisor_uuid(self, load_file, uuid):
        """Viable ec2 platform is determined by /sys/hypervisor/uuid prefix"""
        load_file.return_value = uuid
        instance = UAAutoAttachAWSInstance()
        assert True is instance.is_viable

    @pytest.mark.parametrize(
        "hypervisor_uuid,prod_uuid,prod_serial,viable",
        (
            ("notec2", "ec2UUID", "ec2Serial", True),
            (None, "ec2UUID", "ec2Serial", True),
            ("notec2", "EC2UUID", "Ec2Serial", True),
            (None, "EC2UUID", "Ec2Serial", True),
            ("notec2", "!EC2UUID", "Ec2Serial", False),
            ("notec2", "EC2UUID", "1Ec2Serial", False),
            ("notec2", "ec2UUID", "ec3Serial", False),
            ("notec2", "ec3UUID", "ec2Serial", False),
        ),
    )
    @mock.patch(M_PATH + "system.load_file")
    def test_is_viable_based_on_sys_product_serial_and_uuid(
        self, load_file, hypervisor_uuid, prod_uuid, prod_serial, viable
    ):
        """Platform is viable when product serial and uuid start with ec2"""

        def fake_load_file(f_name):
            if f_name == "/sys/hypervisor/uuid":
                if hypervisor_uuid is not None:
                    return hypervisor_uuid
                raise FileNotFoundError()
            if f_name == "/sys/class/dmi/id/product_uuid":
                return prod_uuid
            if f_name == "/sys/class/dmi/id/product_serial":
                return prod_serial
            raise AssertionError("Invalid load_file of {}".format(f_name))

        load_file.side_effect = fake_load_file
        instance = UAAutoAttachAWSInstance()
        assert viable is instance.is_viable

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch(M_PATH + "http.readurl")
    def test_identity_doc_default_to_ipv6_if_ipv4_fail(
        self, readurl, caplog_text
    ):
        instance = UAAutoAttachAWSInstance()
        ipv4_address = IMDS_IPV4_ADDRESS
        ipv6_address = IMDS_IPV6_ADDRESS

        def fake_someurlerrors(url, method=None, headers=None, timeout=1):
            if ipv4_address in url:
                raise Exception("IPv4 exception")

            if url == IMDS_V2_TOKEN_URL.format(ipv6_address):
                return http.HTTPResponse(
                    code=200,
                    headers={"header": "stuff"},
                    body="base64token==",
                    json_dict={},
                    json_list=[],
                )

            if url == IMDS_URL.format(ipv6_address):
                return http.HTTPResponse(
                    code=200,
                    headers={"header": "stuff"},
                    body="pkcs7WOOT!==",
                    json_dict={},
                    json_list=[],
                )

        readurl.side_effect = fake_someurlerrors
        assert {"pkcs7": "pkcs7WOOT!=="} == instance.identity_doc
        expected = [
            mock.call(
                IMDS_V2_TOKEN_URL.format(ipv4_address),
                method="PUT",
                headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
                timeout=1,
            ),
            mock.call(
                IMDS_V2_TOKEN_URL.format(ipv6_address),
                method="PUT",
                headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
                timeout=1,
            ),
            mock.call(
                IMDS_URL.format(ipv6_address),
                headers={AWS_TOKEN_PUT_HEADER: "base64token=="},
                timeout=1,
            ),
        ]

        assert expected == readurl.call_args_list

        expected_log = "Could not reach AWS IMDS at http://169.254.169.254:"
        assert expected_log in caplog_text()

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch(M_PATH + "http.readurl")
    def test_identity_doc_logs_error_if_both_ipv4_and_ipv6_fails(
        self, readurl, caplog_text
    ):

        instance = UAAutoAttachAWSInstance()
        ipv4_address = IMDS_IPV4_ADDRESS
        ipv6_address = IMDS_IPV6_ADDRESS

        readurl.side_effect = Exception("Exception")

        expected_error = (
            "No valid AWS IMDS endpoint discovered at "
            "addresses: {}, {}".format(IMDS_IPV4_ADDRESS, IMDS_IPV6_ADDRESS)
        )
        with pytest.raises(
            exceptions.UbuntuProError, match=re.escape(expected_error)
        ):
            instance.identity_doc

        expected = [
            mock.call(
                IMDS_V2_TOKEN_URL.format(ipv4_address),
                method="PUT",
                headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
                timeout=1,
            ),
            mock.call(
                IMDS_V2_TOKEN_URL.format(ipv6_address),
                method="PUT",
                headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
                timeout=1,
            ),
        ]
        assert expected == readurl.call_args_list

        expected_logs = [
            "Could not reach AWS IMDS at http://169.254.169.254:",
            "Could not reach AWS IMDS at http://[fd00:ec2::254]:",
        ]

        for expected_log in expected_logs:
            assert expected_log in caplog_text()

    def test_unsupported_should_poll_for_pro_license(self):
        """Unsupported"""
        instance = UAAutoAttachAWSInstance()
        assert not instance.should_poll_for_pro_license()

    def test_unsupported_is_pro_license_present(self):
        """Unsupported"""
        instance = UAAutoAttachAWSInstance()
        with pytest.raises(exceptions.InPlaceUpgradeNotSupportedError):
            instance.is_pro_license_present(wait_for_change=False)

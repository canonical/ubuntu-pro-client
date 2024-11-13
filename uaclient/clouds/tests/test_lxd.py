import mock
import pytest

from uaclient import exceptions, http
from uaclient.clouds.lxd import LXDAutoAttachInstance
from uaclient.testing import helpers

M_PATH = "uaclient.clouds.lxd."


class TestLXDAutoAttachInstance:
    def test_is_viable(self):
        instance = LXDAutoAttachInstance()
        assert instance.is_viable

    def should_poll_for_pro_license(self):
        instance = LXDAutoAttachInstance()
        assert instance.should_poll_for_pro_license()

    @pytest.mark.parametrize(
        [
            "wait_for_change",
            "response",
            "expected_raises",
            "expected_result",
        ],
        [
            (
                True,
                http.HTTPResponse(
                    code=200, headers={}, body="", json_dict={}, json_list=[]
                ),
                pytest.raises(exceptions.CancelProLicensePolling),
                None,
            ),
            (
                False,
                http.HTTPResponse(
                    code=400, headers={}, body="", json_dict={}, json_list=[]
                ),
                helpers.does_not_raise(),
                False,
            ),
            (
                False,
                http.HTTPResponse(
                    code=200, headers={}, body="", json_dict={}, json_list=[]
                ),
                helpers.does_not_raise(),
                False,
            ),
            (
                False,
                http.HTTPResponse(
                    code=200,
                    headers={},
                    body="",
                    json_dict={"guest_attach": "off"},
                    json_list=[],
                ),
                helpers.does_not_raise(),
                False,
            ),
            (
                False,
                http.HTTPResponse(
                    code=200,
                    headers={},
                    body="",
                    json_dict={"guest_attach": "on"},
                    json_list=[],
                ),
                helpers.does_not_raise(),
                True,
            ),
            (
                False,
                http.HTTPResponse(
                    code=200,
                    headers={},
                    body="",
                    json_dict={"guest_attach": "available"},
                    json_list=[],
                ),
                helpers.does_not_raise(),
                False,
            ),
        ],
    )
    @mock.patch(M_PATH + "http.unix_socket_request")
    def test_is_pro_license_present(
        self,
        m_unix_socket_request,
        wait_for_change,
        response,
        expected_raises,
        expected_result,
    ):
        m_unix_socket_request.return_value = response
        instance = LXDAutoAttachInstance()
        with expected_raises:
            assert expected_result == instance.is_pro_license_present(
                wait_for_change=wait_for_change
            )

    @pytest.mark.parametrize(
        [
            "response",
            "expected_raises",
            "expected_result",
        ],
        [
            (
                http.HTTPResponse(
                    code=404, headers={}, body="", json_dict={}, json_list=[]
                ),
                pytest.raises(exceptions.LXDAutoAttachNotAvailable),
                None,
            ),
            (
                http.HTTPResponse(
                    code=403, headers={}, body="", json_dict={}, json_list=[]
                ),
                pytest.raises(exceptions.LXDAutoAttachNotAllowed),
                None,
            ),
            (
                http.HTTPResponse(
                    code=200,
                    headers={},
                    body="",
                    json_dict={"guest_token": "token"},
                    json_list=[],
                ),
                helpers.does_not_raise(),
                "token",
            ),
        ],
    )
    @mock.patch(M_PATH + "http.unix_socket_request")
    def test_acquire_pro_token(
        self,
        m_unix_socket_request,
        response,
        expected_raises,
        expected_result,
        FakeConfig,
    ):
        m_unix_socket_request.return_value = response
        instance = LXDAutoAttachInstance()
        with expected_raises:
            assert expected_result == instance.acquire_pro_token(FakeConfig())

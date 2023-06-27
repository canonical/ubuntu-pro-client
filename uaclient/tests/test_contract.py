import copy
import datetime
import socket

import mock
import pytest

from uaclient import exceptions, http, messages, util
from uaclient.contract import (
    API_V1_AVAILABLE_RESOURCES,
    API_V1_GET_CONTRACT_USING_TOKEN,
    UAContractClient,
    _create_attach_forbidden_message,
    _get_override_weight,
    apply_contract_overrides,
    get_available_resources,
    get_contract_information,
    is_contract_changed,
    process_entitlement_delta,
    refresh,
)
from uaclient.entitlements.base import UAEntitlement
from uaclient.status import UserFacingStatus
from uaclient.testing import helpers
from uaclient.testing.fakes import FakeContractClient
from uaclient.version import get_version

M_PATH = "uaclient.contract."
M_REPO_PATH = "uaclient.entitlements.repo.RepoEntitlement."


@mock.patch("uaclient.http.serviceclient.UAServiceClient.request_url")
@mock.patch("uaclient.contract.system.get_machine_id")
class TestUAContractClient:
    @pytest.mark.parametrize(
        [
            "request_url_side_effect",
            "expected_raises",
            "expected_result",
        ],
        [
            (
                [
                    http.HTTPResponse(
                        code=200,
                        headers={},
                        body="",
                        json_list=[],
                        json_dict={"test": "value"},
                    )
                ],
                helpers.does_not_raise(),
                {"test": "value"},
            ),
            (
                [
                    http.HTTPResponse(
                        code=400,
                        headers={},
                        body="",
                        json_list=[],
                        json_dict={"test": "value"},
                    )
                ],
                pytest.raises(exceptions.ContractAPIError),
                None,
            ),
            (
                [
                    http.HTTPResponse(
                        code=200,
                        headers={"expires": "date"},
                        body="",
                        json_list=[],
                        json_dict={"test": "value"},
                    )
                ],
                helpers.does_not_raise(),
                {"test": "value", "expires": "date"},
            ),
        ],
    )
    @mock.patch("uaclient.contract.UAContractClient._get_activity_info")
    @mock.patch("uaclient.contract.UAContractClient._get_platform_data")
    @mock.patch("uaclient.contract.UAContractClient.headers")
    def test_update_contract_machine(
        self,
        m_headers,
        m_get_platform_data,
        m_get_activity_info,
        _m_get_machine_id,
        m_request_url,
        request_url_side_effect,
        expected_raises,
        expected_result,
    ):
        m_headers.return_value = {"header": "headerval"}
        m_get_platform_data.return_value = {
            "platform": "data",
            "machineId": "something",
        }
        m_get_activity_info.return_value = mock.sentinel.activity_info
        m_request_url.side_effect = request_url_side_effect

        client = UAContractClient(mock.MagicMock())
        with expected_raises:
            result = client.update_contract_machine(
                "mToken", "cId", mock.sentinel.machine_id
            )

        if expected_result:
            assert expected_result == result

        assert [
            mock.call(
                "/v1/contracts/cId/context/machines/something",
                headers={
                    "header": "headerval",
                    "Authorization": "Bearer mToken",
                },
                method="POST",
                data={
                    "platform": "data",
                    "machineId": "something",
                    "activityInfo": mock.sentinel.activity_info,
                },
            )
        ] == m_request_url.call_args_list
        assert [
            mock.call(mock.sentinel.machine_id)
        ] == m_get_platform_data.call_args_list

    @pytest.mark.parametrize("machine_id_param", (("attach-machine-id")))
    @pytest.mark.parametrize(
        "machine_id_response", (("contract-machine-id"), None)
    )
    @pytest.mark.parametrize(
        "detach,expected_http_method",
        ((None, "POST"), (False, "POST"), (True, "DELETE")),
    )
    @pytest.mark.parametrize("activity_id", ((None), ("test-acid")))
    @mock.patch("uaclient.contract.system.get_release_info")
    @mock.patch.object(UAContractClient, "_get_platform_data")
    def test_get_contract_machine(
        self,
        m_platform_data,
        get_release_info,
        get_machine_id,
        request_url,
        detach,
        expected_http_method,
        machine_id_response,
        machine_id_param,
        activity_id,
        FakeConfig,
    ):
        def fake_platform_data(machine_id):
            machine_id = "machine-id" if not machine_id else machine_id
            return {"machineId": machine_id}

        m_platform_data.side_effect = fake_platform_data
        get_release_info.return_value = mock.MagicMock(
            kernel="kernel",
            series="series",
        )

        get_machine_id.return_value = "machineId"
        machine_token = {"machineTokenInfo": {}}
        if machine_id_response:
            machine_token["machineTokenInfo"][
                "machineId"
            ] = machine_id_response
        request_url.return_value = http.HTTPResponse(
            code=200,
            headers={},
            body="",
            json_dict=machine_token,
            json_list=[],
        )
        kwargs = {
            "machine_token": "mToken",
            "contract_id": "cId",
            "machine_id": machine_id_param,
        }
        cfg = FakeConfig.for_attached_machine()
        client = UAContractClient(cfg)
        resp = client.get_contract_machine(**kwargs)
        assert resp == machine_token

    def test_get_resource_machine_access(
        self, get_machine_id, request_url, FakeConfig
    ):
        """GET from resource-machine-access route to "enable" a service"""
        get_machine_id.return_value = "machineId"
        request_url.return_value = http.HTTPResponse(
            code=200,
            headers={},
            body="",
            json_dict={"test": "response"},
            json_list=[],
        )
        cfg = FakeConfig.for_attached_machine()
        client = UAContractClient(cfg)
        kwargs = {"machine_token": "mToken", "resource": "cis"}
        assert {"test": "response"} == client.get_resource_machine_access(
            **kwargs
        )
        assert {"test": "response"} == cfg.read_cache("machine-access-cis")
        params = {
            "headers": {
                "user-agent": "UA-Client/{}".format(get_version()),
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": "Bearer mToken",
            }
        }
        assert [
            mock.call("/v1/resources/cis/context/machines/machineId", **params)
        ] == request_url.call_args_list

    def test_get_contract_using_token(
        self, _m_machine_id, m_request_url, FakeConfig
    ):
        m_request_url.return_value = http.HTTPResponse(
            code=200,
            headers={},
            body="",
            json_dict={"test": "response"},
            json_list=[],
        )

        cfg = FakeConfig.for_attached_machine()
        client = UAContractClient(cfg)
        params = {
            "headers": {
                "user-agent": "UA-Client/{}".format(get_version()),
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": "Bearer some_token",
            }
        }

        assert {"test": "response"} == client.get_contract_using_token(
            "some_token"
        )
        assert [
            mock.call("/v1/contract", **params)
        ] == m_request_url.call_args_list

    @pytest.mark.parametrize("activity_id", ((None), ("test-acid")))
    @pytest.mark.parametrize(
        "enabled_services", (([]), (["esm-apps", "livepatch"]))
    )
    def test_update_activity_token(
        self,
        get_machine_id,
        request_url,
        activity_id,
        enabled_services,
        FakeConfig,
    ):
        """POST machine activity report to the server."""
        machine_id = "machineId"
        get_machine_id.return_value = machine_id
        request_url.return_value = http.HTTPResponse(
            code=200,
            headers={},
            body="",
            json_dict={
                "activityToken": "test-token",
                "activityID": "test-id",
                "activityPingInterval": 5,
            },
            json_list=[],
        )
        cfg = FakeConfig.for_attached_machine()
        client = UAContractClient(cfg)

        def entitlement_user_facing_status(self):
            if self.name in enabled_services:
                return (UserFacingStatus.ACTIVE, "")
            return (UserFacingStatus.INACTIVE, "")

        with mock.patch.object(
            type(cfg.machine_token_file), "activity_id", activity_id
        ):
            with mock.patch.object(
                UAEntitlement,
                "user_facing_status",
                new=entitlement_user_facing_status,
            ):
                with mock.patch(
                    "uaclient.config.files.MachineTokenFile.write"
                ) as m_write_file:
                    client.update_activity_token()

        expected_write_calls = 1
        assert expected_write_calls == m_write_file.call_count

        expected_activity_id = activity_id if activity_id else machine_id
        params = {
            "headers": {
                "user-agent": "UA-Client/{}".format(get_version()),
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": "Bearer not-null",
            },
            "data": {
                "activityToken": None,
                "activityID": expected_activity_id,
                "resources": enabled_services,
            },
        }
        assert [
            mock.call("/v1/contracts/cid/machine-activity/machineId", **params)
        ] == request_url.call_args_list

    @pytest.mark.parametrize(
        [
            "request_url_side_effect",
            "expected_create_attach_forbidden_message_call_args",
            "expected_raises",
            "expected_result",
        ],
        [
            (
                [
                    http.HTTPResponse(
                        code=200,
                        headers={},
                        body="",
                        json_list=[],
                        json_dict={"test": "value"},
                    )
                ],
                [],
                helpers.does_not_raise(),
                {"test": "value"},
            ),
            (
                [
                    http.HTTPResponse(
                        code=401,
                        headers={},
                        body="",
                        json_list=[],
                        json_dict={"test": "value"},
                    )
                ],
                [],
                pytest.raises(exceptions.AttachInvalidTokenError),
                None,
            ),
            (
                [
                    http.HTTPResponse(
                        code=403,
                        headers={},
                        body="",
                        json_list=[],
                        json_dict={"test": "value"},
                    )
                ],
                [mock.call(mock.ANY)],
                pytest.raises(exceptions.UserFacingError),
                None,
            ),
            (
                [
                    http.HTTPResponse(
                        code=400,
                        headers={},
                        body="",
                        json_list=[],
                        json_dict={"test": "value"},
                    )
                ],
                [],
                pytest.raises(exceptions.ContractAPIError),
                None,
            ),
        ],
    )
    @mock.patch("uaclient.contract._create_attach_forbidden_message")
    @mock.patch("uaclient.contract.UAContractClient._get_platform_data")
    @mock.patch("uaclient.contract.UAContractClient.headers")
    def test_add_contract_machine(
        self,
        m_headers,
        m_get_platform_data,
        m_create_attach_forbidden_message,
        _m_get_machine_id,
        m_request_url,
        request_url_side_effect,
        expected_create_attach_forbidden_message_call_args,
        expected_raises,
        expected_result,
    ):
        m_headers.return_value = {"header": "headerval"}
        m_get_platform_data.return_value = {
            "platform": "data",
        }
        m_request_url.side_effect = request_url_side_effect

        client = UAContractClient(mock.MagicMock())
        with expected_raises:
            result = client.add_contract_machine(
                "cToken", mock.sentinel.machine_id
            )

        if expected_result:
            assert expected_result == result

        assert [
            mock.call(
                "/v1/context/machines/token",
                headers={
                    "header": "headerval",
                    "Authorization": "Bearer cToken",
                },
                data={
                    "platform": "data",
                },
            )
        ] == m_request_url.call_args_list
        assert [
            mock.call(mock.sentinel.machine_id)
        ] == m_get_platform_data.call_args_list
        assert (
            expected_create_attach_forbidden_message_call_args
            == m_create_attach_forbidden_message.call_args_list
        )

    def test_new_magic_attach_token_successfull(
        self,
        get_machine_id,
        request_url,
        FakeConfig,
    ):
        cfg = FakeConfig()
        client = UAContractClient(cfg)
        magic_attach_token_resp = (
            {
                "token": "token",
                "expires": "2100-06-09T18:14:55.323733Z",
                "expiresIn": 600,
                "userCode": "1234",
            },
        )
        request_url.return_value = http.HTTPResponse(
            code=200,
            headers={},
            body="",
            json_dict=magic_attach_token_resp,
            json_list=[],
        )

        assert client.new_magic_attach_token() == magic_attach_token_resp

    @pytest.mark.parametrize(
        "request_side_effect,expected_exception,message",
        (
            (
                exceptions.UrlError("cause", "url"),
                exceptions.ConnectivityError,
                messages.CONNECTIVITY_ERROR,
            ),
            (
                [
                    http.HTTPResponse(
                        code=503,
                        headers={},
                        body="",
                        json_dict={},
                        json_list=[],
                    )
                ],
                exceptions.MagicAttachUnavailable,
                messages.MAGIC_ATTACH_UNAVAILABLE,
            ),
        ),
    )
    def test_new_magic_attach_token_fails(
        self,
        get_machine_id,
        request_url,
        FakeConfig,
        request_side_effect,
        expected_exception,
        message,
    ):
        cfg = FakeConfig()
        client = UAContractClient(cfg)
        request_url.side_effect = request_side_effect

        with pytest.raises(expected_exception) as exc_error:
            client.new_magic_attach_token()

        assert message.msg == exc_error.value.msg
        assert message.name == exc_error.value.msg_code

    @pytest.mark.parametrize(
        "error_code,expected_exception",
        (
            (401, exceptions.MagicAttachTokenError),
            (503, exceptions.MagicAttachUnavailable),
        ),
    )
    def test_get_magic_attach_token_info_contract_error(
        self,
        get_machine_id,
        request_url,
        error_code,
        expected_exception,
        FakeConfig,
    ):
        cfg = FakeConfig()
        client = UAContractClient(cfg)
        magic_token = "test-id"
        request_url.return_value = http.HTTPResponse(
            code=error_code,
            headers={},
            body="",
            json_dict={},
            json_list=[],
        )

        with pytest.raises(expected_exception):
            client.get_magic_attach_token_info(magic_token=magic_token)

    def test_request_magic_attach_id_info_fails(
        self,
        get_machine_id,
        request_url,
        FakeConfig,
    ):
        cfg = FakeConfig()
        client = UAContractClient(cfg)
        magic_token = "test-id"
        request_url.side_effect = exceptions.UrlError("cause", "url")

        with pytest.raises(exceptions.ConnectivityError) as exc_error:
            client.get_magic_attach_token_info(magic_token=magic_token)

        assert messages.CONNECTIVITY_ERROR.msg == exc_error.value.msg
        assert messages.CONNECTIVITY_ERROR.name == exc_error.value.msg_code

    @pytest.mark.parametrize(
        "error_code,expected_exception",
        (
            (400, exceptions.MagicAttachTokenAlreadyActivated),
            (401, exceptions.MagicAttachTokenError),
            (503, exceptions.MagicAttachUnavailable),
        ),
    )
    def test_revoke_magic_attach_token_contract_error(
        self,
        get_machine_id,
        request_url,
        error_code,
        expected_exception,
        FakeConfig,
    ):
        cfg = FakeConfig()
        client = UAContractClient(cfg)
        magic_token = "test-id"
        request_url.return_value = http.HTTPResponse(
            code=error_code,
            headers={},
            body="",
            json_dict={},
            json_list=[],
        )

        with pytest.raises(expected_exception):
            client.revoke_magic_attach_token(magic_token=magic_token)

    def test_revoke_magic_attach_token_fails(
        self,
        get_machine_id,
        request_url,
        FakeConfig,
    ):
        cfg = FakeConfig()
        client = UAContractClient(cfg)
        magic_token = "test-id"
        request_url.side_effect = exceptions.UrlError("cause", "url")

        with pytest.raises(exceptions.ConnectivityError) as exc_error:
            client.revoke_magic_attach_token(magic_token=magic_token)

        assert messages.CONNECTIVITY_ERROR.msg == exc_error.value.msg
        assert messages.CONNECTIVITY_ERROR.name == exc_error.value.msg_code


class TestProcessEntitlementDeltas:
    def test_error_on_missing_entitlement_type(self, FakeConfig):
        """Raise an error when neither dict contains entitlement type."""
        new_access = {"entitlement": {"something": "non-empty"}}
        error_msg = (
            "Could not determine contract delta service type"
            " {{}} {}".format(new_access)
        )
        with pytest.raises(exceptions.UserFacingError) as exc:
            process_entitlement_delta(
                cfg=FakeConfig(), orig_access={}, new_access=new_access
            )
        assert error_msg == str(exc.value.msg)

    def test_no_delta_on_equal_dicts(self, FakeConfig):
        """No deltas are reported or processed when dicts are equal."""
        assert ({}, False) == process_entitlement_delta(
            cfg=FakeConfig(),
            orig_access={"entitlement": {"no": "diff"}},
            new_access={"entitlement": {"no": "diff"}},
        )

    @mock.patch(M_REPO_PATH + "process_contract_deltas")
    def test_deltas_handled_by_entitlement_process_contract_deltas(
        self, m_process_contract_deltas, FakeConfig
    ):
        """Call entitlement.process_contract_deltas to handle any deltas."""
        m_process_contract_deltas.return_value = True
        original_access = {"entitlement": {"type": "esm-infra"}}
        new_access = copy.deepcopy(original_access)
        new_access["entitlement"]["newkey"] = "newvalue"
        expected = {"entitlement": {"newkey": "newvalue"}}
        assert (expected, True) == process_entitlement_delta(
            cfg=FakeConfig(),
            orig_access=original_access,
            new_access=new_access,
        )
        expected_calls = [
            mock.call(original_access, expected, allow_enable=False)
        ]
        assert expected_calls == m_process_contract_deltas.call_args_list

    @mock.patch(M_REPO_PATH + "process_contract_deltas")
    def test_full_delta_on_empty_orig_dict(
        self, m_process_contract_deltas, FakeConfig
    ):
        """Process and report full deltas on empty original access dict."""
        # Limit delta processing logic to handle attached state-A to state-B
        # Fresh installs will have empty/unset
        new_access = {"entitlement": {"type": "esm-infra", "other": "val2"}}
        actual, _ = process_entitlement_delta(
            cfg=FakeConfig(), orig_access={}, new_access=new_access
        )
        assert new_access == actual
        expected_calls = [mock.call({}, new_access, allow_enable=False)]
        assert expected_calls == m_process_contract_deltas.call_args_list

    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="fake_series"),
    )
    @mock.patch(M_REPO_PATH + "process_contract_deltas")
    def test_overrides_applied_before_comparison(
        self, m_process_contract_deltas, _, FakeConfig
    ):
        old_access = {"entitlement": {"type": "esm", "some_key": "some_value"}}
        new_access = {
            "entitlement": {
                "type": "esm",
                "some_key": "will be overridden",
                "series": {"fake_series": {"some_key": "some_value"}},
            }
        }

        process_entitlement_delta(
            cfg=FakeConfig(), orig_access=old_access, new_access=new_access
        )

        assert 0 == m_process_contract_deltas.call_count


class TestCreateAttachForbiddenMessage:
    @pytest.mark.parametrize(
        [
            "http_response",
            "expected_message",
        ],
        [
            (
                http.HTTPResponse(
                    code=403, headers={}, body="", json_list=[], json_dict={}
                ),
                messages.ATTACH_EXPIRED_TOKEN,
            ),
            (
                http.HTTPResponse(
                    code=403,
                    headers={},
                    body="",
                    json_list=[],
                    json_dict={
                        "code": "forbidden",
                        "info": {
                            "contractId": "contract-id",
                            "reason": "no-longer-effective",
                            "time": datetime.datetime(
                                2021,
                                5,
                                7,
                                9,
                                46,
                                37,
                                tzinfo=datetime.timezone.utc,
                            ),
                        },
                        "message": 'contract "contract-id" is no longer effective',  # noqa: E501
                        "traceId": "7f58c084-f753-455d-9bdc-65b839d6536f",
                    },
                ),
                messages.NamedMessage(
                    name=messages.ATTACH_FORBIDDEN_EXPIRED.name,
                    msg=messages.ATTACH_FORBIDDEN.format(
                        reason=messages.ATTACH_FORBIDDEN_EXPIRED.format(
                            contract_id="contract-id", date="May 07, 2021"
                        ).msg
                    ).msg,
                    additional_info={
                        "contract_expiry_date": "05-07-2021",
                        "contract_id": "contract-id",
                    },
                ),
            ),
            (
                http.HTTPResponse(
                    code=403,
                    headers={},
                    body="",
                    json_list=[],
                    json_dict={
                        "code": "forbidden",
                        "info": {
                            "contractId": "contract-id",
                            "reason": "not-effective-yet",
                            "time": datetime.datetime(
                                2021,
                                5,
                                7,
                                9,
                                46,
                                37,
                                tzinfo=datetime.timezone.utc,
                            ),
                        },
                        "message": 'contract "contract-id" is not effective yet',  # noqa: E501
                        "traceId": "7f58c084-f753-455d-9bdc-65b839d6536f",
                    },
                ),
                messages.NamedMessage(
                    name=messages.ATTACH_FORBIDDEN_NOT_YET.name,
                    msg=messages.ATTACH_FORBIDDEN.format(
                        reason=messages.ATTACH_FORBIDDEN_NOT_YET.format(
                            contract_id="contract-id", date="May 07, 2021"
                        ).msg
                    ).msg,
                    additional_info={
                        "contract_effective_date": "05-07-2021",
                        "contract_id": "contract-id",
                    },
                ),
            ),
            (
                http.HTTPResponse(
                    code=403,
                    headers={},
                    body="",
                    json_list=[],
                    json_dict={
                        "code": "forbidden",
                        "info": {
                            "contractId": "contract-id",
                            "reason": "never-effective",
                        },
                        "message": 'contract "contract-id" is was never effective',  # noqa: E501
                        "traceId": "7f58c084-f753-455d-9bdc-65b839d6536f",
                    },
                ),
                messages.NamedMessage(
                    name=messages.ATTACH_FORBIDDEN_NEVER.name,
                    msg=messages.ATTACH_FORBIDDEN.format(
                        reason=messages.ATTACH_FORBIDDEN_NEVER.format(
                            contract_id="contract-id"
                        ).msg
                    ).msg,
                ),
            ),
        ],
    )
    def test_create_attach_forbidden_message(
        self, http_response, expected_message
    ):
        assert expected_message == _create_attach_forbidden_message(
            http_response
        )


class TestGetAvailableResources:
    @mock.patch.object(UAContractClient, "available_resources")
    def test_available_resources_error_on_network_disconnected(
        self, m_available_resources, FakeConfig
    ):
        """Raise error get_available_resources can't contact backend"""
        cfg = FakeConfig()

        urlerror = exceptions.UrlError(
            socket.gaierror(-2, "Name or service not known"), "url"
        )
        m_available_resources.side_effect = urlerror

        with pytest.raises(exceptions.UrlError) as exc:
            get_available_resources(cfg)
        assert urlerror == exc.value

    @mock.patch(M_PATH + "UAContractClient")
    def test_available_resources_from_contract_server(
        self, client, FakeConfig
    ):
        """Call get_available_resources to get updated resources."""
        cfg = FakeConfig()

        url = API_V1_AVAILABLE_RESOURCES

        new_resources = [{"name": "new_resource", "available": False}]

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {url: {"resources": new_resources}}
            return fake_client

        client.side_effect = fake_contract_client
        assert new_resources == get_available_resources(cfg)


class TestGetContractInformation:
    @mock.patch(M_PATH + "UAContractClient")
    def test_get_contract_information_from_contract_server(
        self, m_client, FakeConfig
    ):
        cfg = FakeConfig()

        url = API_V1_GET_CONTRACT_USING_TOKEN

        information = {"contract": "some_contract_data"}

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {url: information}

            return fake_client

        m_client.side_effect = fake_contract_client
        assert information == get_contract_information(cfg, "some_token")


class TestRefresh:
    @pytest.mark.parametrize(
        [
            "update_contract_machine_result",
            "expected_write_cache_call_args",
        ],
        [
            (
                {"response": "val"},
                [mock.call("machine-id", mock.sentinel.system_machine_id)],
            ),
            (
                {
                    "response": "val",
                    "machineTokenInfo": {
                        "machineId": mock.sentinel.response_machine_id
                    },
                },
                [mock.call("machine-id", mock.sentinel.response_machine_id)],
            ),
        ],
    )
    @mock.patch(M_PATH + "process_entitlements_delta")
    @mock.patch(M_PATH + "UAConfig.write_cache")
    @mock.patch(M_PATH + "system.get_machine_id")
    @mock.patch("uaclient.files.MachineTokenFile.write")
    @mock.patch(M_PATH + "UAContractClient.update_contract_machine")
    @mock.patch(
        M_PATH + "UAConfig.machine_token", new_callable=mock.PropertyMock
    )
    @mock.patch(
        "uaclient.files.MachineTokenFile.entitlements",
        new_callable=mock.PropertyMock,
    )
    def test_refresh(
        self,
        m_entitlements,
        m_machine_token,
        m_update_contract_machine,
        m_machine_token_file_write,
        m_get_machine_id,
        m_write_cache,
        m_process_entitlements_deltas,
        update_contract_machine_result,
        expected_write_cache_call_args,
        FakeConfig,
    ):
        m_entitlements.side_effect = [
            mock.sentinel.orig_entitlements,
            mock.sentinel.new_entitlements,
        ]
        m_machine_token.return_value = {
            "machineToken": "mToken",
            "machineTokenInfo": {"contractInfo": {"id": "cId"}},
        }
        m_update_contract_machine.return_value = update_contract_machine_result
        m_get_machine_id.return_value = mock.sentinel.system_machine_id

        refresh(FakeConfig())

        assert [
            mock.call(machine_token="mToken", contract_id="cId")
        ] == m_update_contract_machine.call_args_list
        assert [
            mock.call(update_contract_machine_result)
        ] == m_machine_token_file_write.call_args_list
        assert expected_write_cache_call_args == m_write_cache.call_args_list
        assert [
            mock.call(
                mock.ANY,
                mock.sentinel.orig_entitlements,
                mock.sentinel.new_entitlements,
                allow_enable=False,
            )
        ] == m_process_entitlements_deltas.call_args_list


@mock.patch("uaclient.contract.UAContractClient.get_contract_machine")
class TestContractChanged:
    @pytest.mark.parametrize("has_contract_expired", (False, True))
    def test_contract_change_with_expiry(
        self, m_get_contract_machine, has_contract_expired, FakeConfig
    ):
        if has_contract_expired:
            expiry_date = util.parse_rfc3339_date("2041-05-08T19:02:26Z")
            ret_val = True
        else:
            expiry_date = util.parse_rfc3339_date("2040-05-08T19:02:26Z")
            ret_val = False
        m_get_contract_machine.return_value = {
            "machineTokenInfo": {
                "contractInfo": {
                    "effectiveTo": expiry_date,
                },
            },
        }
        cfg = FakeConfig().for_attached_machine()
        assert is_contract_changed(cfg) == ret_val

    @pytest.mark.parametrize("has_contract_changed", (False, True))
    def test_contract_change_with_entitlements(
        self, m_get_contract_machine, has_contract_changed, FakeConfig
    ):
        if has_contract_changed:
            resourceEntitlements = [{"type": "token1", "entitled": True}]
            resourceTokens = [{"token": "token1", "type": "resource1"}]
        else:
            resourceTokens = []
            resourceEntitlements = []
        m_get_contract_machine.return_value = {
            "machineTokenInfo": {
                "machineId": "test_machine_id",
                "resourceTokens": resourceTokens,
                "contractInfo": {
                    "effectiveTo": util.parse_rfc3339_date(
                        "2040-05-08T19:02:26Z"
                    ),
                    "resourceEntitlements": resourceEntitlements,
                },
            },
        }
        cfg = FakeConfig().for_attached_machine()
        assert is_contract_changed(cfg) == has_contract_changed


class TestApplyContractOverrides:
    @pytest.mark.parametrize(
        "override_selector,expected_weight",
        (
            ({"selector1": "valueX", "selector2": "valueZ"}, 0),
            ({"selector1": "valueA", "selector2": "valueZ"}, 0),
            ({"selector1": "valueX", "selector2": "valueB"}, 0),
            ({"selector1": "valueA"}, 1),
            ({"selector2": "valueB"}, 2),
            ({"selector1": "valueA", "selector2": "valueB"}, 3),
        ),
    )
    def test_get_override_weight(self, override_selector, expected_weight):
        selector_values = {"selector1": "valueA", "selector2": "valueB"}
        selector_weights = {"selector1": 1, "selector2": 2}
        with mock.patch(
            "uaclient.contract.OVERRIDE_SELECTOR_WEIGHTS", selector_weights
        ):
            assert expected_weight == _get_override_weight(
                override_selector, selector_values
            )

    def test_error_on_non_entitlement_dict(self):
        """Raise a runtime error when seeing invalid dict type."""
        with pytest.raises(RuntimeError) as exc:
            apply_contract_overrides({"some": "dict"})
        error = (
            'Expected entitlement access dict. Missing "entitlement" key:'
            " {'some': 'dict'}"
        )
        assert error == str(exc.value)

    @pytest.mark.parametrize("include_overrides", (True, False))
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="ubuntuX"),
    )
    @mock.patch(
        "uaclient.clouds.identity.get_cloud_type", return_value=(None, "")
    )
    def test_return_same_dict_when_no_overrides_match(
        self, _m_cloud_type, _m_release_info, include_overrides
    ):
        orig_access = {
            "entitlement": {
                "affordances": {"some_affordance": ["ubuntuX"]},
                "directives": {"some_directive": ["ubuntuX"]},
                "obligations": {"some_obligation": False},
            }
        }
        # exactly the same
        expected = {
            "entitlement": {
                "affordances": {"some_affordance": ["ubuntuX"]},
                "directives": {"some_directive": ["ubuntuX"]},
                "obligations": {"some_obligation": False},
            }
        }
        if include_overrides:
            overrides = [
                {
                    "selector": {"series": "dontMatch"},
                    "affordances": {
                        "some_affordance": ["ubuntuX-series-overriden"]
                    },
                },
                {
                    "selector": {"cloud": "dontMatch"},
                    "affordances": {
                        "some_affordance": ["ubuntuX-cloud-overriden"]
                    },
                },
            ]

            orig_access["entitlement"].update(
                {
                    "series": {
                        "dontMatch": {
                            "affordances": {
                                "some_affordance": ["ubuntuX-series-overriden"]
                            }
                        }
                    },
                    "overrides": overrides,
                }
            )
            expected["entitlement"]["overrides"] = overrides

        apply_contract_overrides(orig_access)
        assert expected == orig_access

    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="ubuntuX"),
    )
    def test_missing_keys_are_included(self, _m_release_info):
        orig_access = {
            "entitlement": {
                "series": {"ubuntuX": {"directives": {"suites": ["ubuntuX"]}}}
            }
        }
        expected = {"entitlement": {"directives": {"suites": ["ubuntuX"]}}}

        apply_contract_overrides(orig_access)

        assert expected == orig_access

    @pytest.mark.parametrize(
        "series_selector,cloud_selector,series_cloud_selector,expected_value",
        (
            # apply_overrides_when_only_series_match
            ("no-match", "no-match", "no-match", "old_series_overriden"),
            # series selector is applied over old series override
            ("ubuntuX", "no-match", "no-match", "series_overriden"),
            # cloud selector is applied over series override
            ("no-match", "cloudX", "no-match", "cloud_overriden"),
            # cloud selector is applied over series selector
            ("ubuntuX", "cloudX", "no-match", "cloud_overriden"),
            # cloud and series together are applied over others
            ("ubuntuX", "cloudX", "cloudX", "both_overriden"),
        ),
    )
    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="ubuntuX"),
    )
    @mock.patch(
        "uaclient.clouds.identity.get_cloud_type",
        return_value=("cloudX", None),
    )
    def test_applies_contract_overrides_respecting_weight(
        self,
        _m_cloud_type,
        _m_release_info,
        series_selector,
        cloud_selector,
        series_cloud_selector,
        expected_value,
    ):
        """Apply the expected overrides to orig_access dict when called."""
        overrides = [
            {
                "selector": {"series": series_selector},
                "affordances": {"some_affordance": ["series_overriden"]},
            },
            {
                "selector": {"cloud": cloud_selector},
                "affordances": {"some_affordance": ["cloud_overriden"]},
            },
            {
                "selector": {
                    "series": series_selector,
                    "cloud": series_cloud_selector,
                },
                "affordances": {"some_affordance": ["both_overriden"]},
            },
        ]

        orig_access = {
            "entitlement": {
                "affordances": {"some_affordance": ["original_affordance"]},
                "series": {
                    "ubuntuX": {
                        "affordances": {
                            "some_affordance": ["old_series_overriden"]
                        }
                    }
                },
                "overrides": overrides,
            }
        }

        expected = {
            "entitlement": {
                "affordances": {"some_affordance": [expected_value]},
                "overrides": overrides,
            }
        }

        apply_contract_overrides(orig_access)
        assert orig_access == expected

    @mock.patch(
        "uaclient.system.get_release_info",
        return_value=mock.MagicMock(series="ubuntuX"),
    )
    @mock.patch(
        "uaclient.clouds.identity.get_cloud_type",
        return_value=("cloudX", None),
    )
    def test_different_overrides_applied_together(
        self, _m_cloud_type, _m_release_info
    ):
        """Apply different overrides from different matching selectors."""
        overrides = [
            {
                "selector": {"series": "ubuntuX"},
                "affordances": {"some_affordance": ["series_overriden"]},
            },
            {
                "selector": {"cloud": "cloudX"},
                "directives": {"some_directive": ["cloud_overriden"]},
            },
            {
                "selector": {"series": "ubuntuX", "cloud": "cloudX"},
                "obligations": {
                    "new_obligation": True,
                    "some_obligation": True,
                },
            },
        ]

        orig_access = {
            "entitlement": {
                "affordances": {"some_affordance": ["original_affordance"]},
                "directives": {"some_directive": ["original_directive"]},
                "obligations": {"some_obligation": False},
                "series": {
                    "ubuntuX": {
                        "affordances": {
                            "new_affordance": ["new_affordance_value"]
                        }
                    }
                },
                "overrides": overrides,
            }
        }

        expected = {
            "entitlement": {
                "affordances": {
                    "new_affordance": ["new_affordance_value"],
                    "some_affordance": ["series_overriden"],
                },
                "directives": {"some_directive": ["cloud_overriden"]},
                "obligations": {
                    "new_obligation": True,
                    "some_obligation": True,
                },
                "overrides": overrides,
            }
        }

        apply_contract_overrides(orig_access)
        assert orig_access == expected


@mock.patch("uaclient.http.serviceclient.UAServiceClient.request_url")
class TestRequestAutoAttach:
    @mock.patch("uaclient.contract.logging.debug")
    def test_request_for_invalid_pro_image(
        self, m_logging_debug, m_request_url, FakeConfig
    ):
        cfg = FakeConfig()
        contract = UAContractClient(cfg)

        error_response = {
            "code": "contract not found",
            "message": (
                'missing product mapping for subscription "test", '
                'plan "pro-image", product "pro-product", '
                'publisher "canonical", sku "pro-sku"'
            ),
        }
        m_request_url.return_value = http.HTTPResponse(
            code=400,
            headers={},
            body="",
            json_dict=error_response,
            json_list=[],
        )

        with pytest.raises(exceptions.InvalidProImage) as exc_error:
            contract.get_contract_token_for_cloud_instance(
                instance=mock.MagicMock()
            )

        expected_message = messages.INVALID_PRO_IMAGE.format(
            msg=error_response["message"]
        )
        expected_args = [mock.call(error_response["message"])]
        assert expected_message.msg == exc_error.value.msg
        assert expected_args == m_logging_debug.call_args_list
        assert exc_error.value.msg_code == "invalid-pro-image"

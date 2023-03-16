import copy
import json
import logging
import socket

import mock
import pytest

from uaclient import exceptions, messages, util
from uaclient.contract import (
    API_V1_CONTEXT_MACHINE_TOKEN,
    API_V1_CONTRACT_INFORMATION,
    API_V1_RESOURCES,
    API_V1_TMPL_CONTEXT_MACHINE_TOKEN_RESOURCE,
    API_V1_TMPL_RESOURCE_MACHINE_ACCESS,
    UAContractClient,
    _get_override_weight,
    apply_contract_overrides,
    get_available_resources,
    get_contract_information,
    is_contract_changed,
    process_entitlement_delta,
    request_updated_contract,
)
from uaclient.entitlements.base import UAEntitlement
from uaclient.messages import (
    ATTACH_EXPIRED_TOKEN,
    ATTACH_FAILURE_DEFAULT_SERVICES,
    ATTACH_FORBIDDEN,
    ATTACH_FORBIDDEN_EXPIRED,
    ATTACH_FORBIDDEN_NEVER,
    ATTACH_FORBIDDEN_NOT_YET,
    ATTACH_INVALID_TOKEN,
    INVALID_PRO_IMAGE,
    UNEXPECTED_ERROR,
)
from uaclient.status import UserFacingStatus
from uaclient.testing.fakes import FakeContractClient
from uaclient.version import get_version

M_PATH = "uaclient.contract."
M_REPO_PATH = "uaclient.entitlements.repo.RepoEntitlement."


@mock.patch("uaclient.serviceclient.UAServiceClient.request_url")
@mock.patch("uaclient.contract.system.get_machine_id")
class TestUAContractClient:
    @pytest.mark.parametrize(
        "machine_id_response", (("contract-machine-id"), None)
    )
    @pytest.mark.parametrize("activity_id", ((None), ("test-acid")))
    @mock.patch("uaclient.contract.system.get_virt_type")
    @mock.patch("uaclient.contract.system.get_dpkg_arch")
    @mock.patch("uaclient.contract.system.get_kernel_info")
    @mock.patch("uaclient.contract.system.get_release_info")
    def test__request_machine_token_update(
        self,
        m_get_release_info,
        m_get_kernel_info,
        m_get_dpkg_arch,
        m_get_virt_type,
        m_get_machine_id,
        m_request_url,
        machine_id_response,
        activity_id,
        FakeConfig,
    ):
        """POST or DELETE to ua-contracts and write machine-token cache.

        Setting detach=True will result in a DELETE operation.
        """
        m_get_release_info.return_value = mock.MagicMock(
            distribution="Ubuntu",
            release="release",
            series="series",
            pretty_version="version",
        )
        m_get_kernel_info.return_value = mock.MagicMock(uname_release="kernel")
        m_get_dpkg_arch.return_value = "arch"
        m_get_virt_type.return_value = "virt"
        m_get_machine_id.return_value = "machineId"

        machine_token = {"machineTokenInfo": {}}
        if machine_id_response:
            machine_token["machineTokenInfo"][
                "machineId"
            ] = machine_id_response

        m_request_url.return_value = (machine_token, {})
        cfg = FakeConfig.for_attached_machine()
        client = UAContractClient(cfg)
        kwargs = {"machine_token": "mToken", "contract_id": "cId"}
        enabled_services = ["esm-apps", "livepatch"]

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
                client._request_machine_token_update(**kwargs)

        assert machine_token != cfg.machine_token_file.machine_token
        client.update_files_after_machine_token_update(machine_token)
        assert machine_token == cfg.machine_token_file.machine_token
        expected_machine_id = "machineId"
        if machine_id_response:
            expected_machine_id = machine_id_response

        assert expected_machine_id == cfg.read_cache("machine-id")
        params = {
            "headers": {
                "user-agent": "UA-Client/{}".format(get_version()),
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": "Bearer mToken",
            },
            "method": "POST",
        }
        expected_activity_id = activity_id if activity_id else "machineId"
        params["data"] = {
            "machineId": "machineId",
            "architecture": "arch",
            "os": {
                "type": "Linux",
                "kernel": "kernel",
                "distribution": "Ubuntu",
                "release": "release",
                "series": "series",
                "version": "version",
                "virt": "virt",
            },
            "activityInfo": {
                "activityToken": None,
                "activityID": expected_activity_id,
                "resources": enabled_services,
            },
        }
        assert m_request_url.call_args_list == [
            mock.call("/v1/contracts/cId/context/machines/machineId", **params)
        ]

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
    def test_get_updated_contract_info(
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
        request_url.return_value = (machine_token, {})
        kwargs = {
            "machine_token": "mToken",
            "contract_id": "cId",
            "machine_id": machine_id_param,
        }
        cfg = FakeConfig.for_attached_machine()
        client = UAContractClient(cfg)
        resp = client.get_updated_contract_info(**kwargs)
        assert resp == machine_token

    def test_request_resource_machine_access(
        self, get_machine_id, request_url, FakeConfig
    ):
        """GET from resource-machine-access route to "enable" a service"""
        get_machine_id.return_value = "machineId"
        request_url.return_value = ("response", {})
        cfg = FakeConfig.for_attached_machine()
        client = UAContractClient(cfg)
        kwargs = {"machine_token": "mToken", "resource": "cis"}
        assert "response" == client.request_resource_machine_access(**kwargs)
        assert "response" == cfg.read_cache("machine-access-cis")
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

    def test_request_contract_information(
        self, _m_machine_id, m_request_url, FakeConfig
    ):
        m_request_url.return_value = ("response", {})

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

        assert "response" == client.request_contract_information("some_token")
        assert [
            mock.call("/v1/contract", **params)
        ] == m_request_url.call_args_list

    @pytest.mark.parametrize("activity_id", ((None), ("test-acid")))
    @pytest.mark.parametrize(
        "enabled_services", (([]), (["esm-apps", "livepatch"]))
    )
    def test_report_machine_activity(
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
        request_url.return_value = (
            {
                "activityToken": "test-token",
                "activityID": "test-id",
                "activityPingInterval": 5,
            },
            None,
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
                    client.report_machine_activity()

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

    @pytest.mark.parametrize("machine_id_param", (("attach-machine-id"), None))
    @pytest.mark.parametrize(
        "machine_id_response", (("contract-machine-id"), None)
    )
    @mock.patch.object(UAContractClient, "_get_platform_data")
    def test__request_contract_machine_attach(
        self,
        m_platform_data,
        get_machine_id,
        request_url,
        machine_id_response,
        machine_id_param,
        FakeConfig,
    ):
        def fake_platform_data(machine_id):
            machine_id = "machine-id" if not machine_id else machine_id
            return {"machineId": machine_id}

        m_platform_data.side_effect = fake_platform_data

        machine_token = {"machineTokenInfo": {}}
        if machine_id_response:
            machine_token["machineTokenInfo"][
                "machineId"
            ] = machine_id_response

        request_url.return_value = (machine_token, {})
        contract_token = "mToken"

        params = {
            "data": fake_platform_data(machine_id_param),
            "headers": {
                "user-agent": "UA-Client/{}".format(get_version()),
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": "Bearer mToken",
            },
        }

        cfg = FakeConfig()
        client = UAContractClient(cfg)
        client.request_contract_machine_attach(
            contract_token=contract_token, machine_id=machine_id_param
        )

        assert [
            mock.call("/v1/context/machines/token", **params)
        ] == request_url.call_args_list

        expected_machine_id = "contract-machine-id"
        if not machine_id_response:
            if machine_id_param:
                expected_machine_id = machine_id_param
            else:
                expected_machine_id = "machine-id"

        assert expected_machine_id == cfg.read_cache("machine-id")

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
        request_url.return_value = (magic_attach_token_resp, None)

        assert client.new_magic_attach_token() == magic_attach_token_resp

    @pytest.mark.parametrize(
        "raised_exception,expected_exception,message",
        (
            (
                exceptions.UrlError("test"),
                exceptions.ConnectivityError,
                messages.CONNECTIVITY_ERROR,
            ),
            (
                exceptions.ContractAPIError(
                    exceptions.UrlError("test", code=503),
                    error_response={},
                ),
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
        raised_exception,
        expected_exception,
        message,
    ):
        cfg = FakeConfig()
        client = UAContractClient(cfg)
        request_url.side_effect = raised_exception

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
        request_url.side_effect = exceptions.ContractAPIError(
            exceptions.UrlError("test", error_code),
            error_response={},
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
        request_url.side_effect = exceptions.UrlError("test")

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
        request_url.side_effect = exceptions.ContractAPIError(
            exceptions.UrlError("test", error_code),
            error_response={},
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
        request_url.side_effect = exceptions.UrlError("test")

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


class TestGetAvailableResources:
    @mock.patch.object(UAContractClient, "request_resources")
    def test_request_resources_error_on_network_disconnected(
        self, m_request_resources, FakeConfig
    ):
        """Raise error get_available_resources can't contact backend"""
        cfg = FakeConfig()

        urlerror = exceptions.UrlError(
            socket.gaierror(-2, "Name or service not known")
        )
        m_request_resources.side_effect = urlerror

        with pytest.raises(exceptions.UrlError) as exc:
            get_available_resources(cfg)
        assert urlerror == exc.value

    @mock.patch(M_PATH + "UAContractClient")
    def test_request_resources_from_contract_server(self, client, FakeConfig):
        """Call UAContractClient.request_resources to get updated resources."""
        cfg = FakeConfig()

        url = API_V1_RESOURCES

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

        url = API_V1_CONTRACT_INFORMATION

        information = {"contract": "some_contract_data"}

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {url: information}

            return fake_client

        m_client.side_effect = fake_contract_client
        assert information == get_contract_information(cfg, "some_token")


class TestRequestUpdatedContract:

    refresh_route = API_V1_TMPL_CONTEXT_MACHINE_TOKEN_RESOURCE.format(
        contract="cid", machine="mid"
    )
    access_route_ent1 = API_V1_TMPL_RESOURCE_MACHINE_ACCESS.format(
        resource="ent1", machine="mid"
    )
    access_route_ent2 = API_V1_TMPL_RESOURCE_MACHINE_ACCESS.format(
        resource="ent2", machine="mid"
    )

    @mock.patch(M_PATH + "UAContractClient")
    def test_attached_config_and_contract_token_runtime_error(
        self, client, FakeConfig
    ):
        """When attached, error if called with a contract_token."""

        def fake_contract_client(cfg):
            return FakeContractClient(cfg)

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as exc:
            request_updated_contract(cfg, contract_token="something")

        expected_msg = (
            "Got unexpected contract_token on an already attached machine"
        )
        assert expected_msg == str(exc.value.msg)

    @pytest.mark.parametrize(
        "error_code, error_msg, error_response",
        (
            (401, ATTACH_INVALID_TOKEN, '{"message": "unauthorized"}'),
            (403, ATTACH_EXPIRED_TOKEN, "{}"),
            (
                403,
                ATTACH_FORBIDDEN.format(
                    reason=ATTACH_FORBIDDEN_EXPIRED.format(
                        contract_id="contract-id", date="May 07, 2021"
                    ).msg
                ),
                """{
                "code": "forbidden",
                "info": {
                    "contractId": "contract-id",
                    "reason": "no-longer-effective",
                    "time": "2021-05-07T09:46:37.791Z"
                },
                "message": "contract \\"contract-id\\" is no longer effective",
                "traceId": "7f58c084-f753-455d-9bdc-65b839d6536f"
                }""",
            ),
            (
                403,
                ATTACH_FORBIDDEN.format(
                    reason=ATTACH_FORBIDDEN_NOT_YET.format(
                        contract_id="contract-id", date="May 07, 2021"
                    ).msg
                ),
                """{
                "code": "forbidden",
                "info": {
                    "contractId": "contract-id",
                    "reason": "not-effective-yet",
                    "time": "2021-05-07T09:46:37.791Z"
                },
                "message": "contract \\"contract-id\\" is not effective yet",
                "traceId": "7f58c084-f753-455d-9bdc-65b839d6536f"
                }""",
            ),
            (
                403,
                ATTACH_FORBIDDEN.format(
                    reason=ATTACH_FORBIDDEN_NEVER.format(
                        contract_id="contract-id"
                    ).msg
                ),
                """{
                "code": "forbidden",
                "info": {
                    "contractId": "contract-id",
                    "reason": "never-effective"
                },
                "message": "contract \\"contract-id\\" is was never effective",
                "traceId": "7f58c084-f753-455d-9bdc-65b839d6536f"
            }""",
            ),
        ),
    )
    @mock.patch("uaclient.system.get_machine_id", return_value="mid")
    @mock.patch(M_PATH + "UAContractClient")
    def test_invalid_token_user_facing_error_on_invalid_token_refresh_failure(
        self,
        client,
        get_machine_id,
        FakeConfig,
        error_code,
        error_msg,
        error_response,
    ):
        """When attaching, invalid token errors result in proper user error."""

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {
                API_V1_CONTEXT_MACHINE_TOKEN: exceptions.ContractAPIError(
                    exceptions.UrlError(
                        "Server error",
                        code=error_code,
                        url="http://me",
                        headers={},
                    ),
                    error_response=json.loads(
                        error_response, cls=util.DatetimeAwareJSONDecoder
                    ),
                )
            }
            return fake_client

        client.side_effect = fake_contract_client
        cfg = FakeConfig()
        with pytest.raises(exceptions.UserFacingError) as exc:
            request_updated_contract(cfg, contract_token="yep")

        assert error_msg.msg == str(exc.value.msg)

    @mock.patch("uaclient.system.get_machine_id", return_value="mid")
    @mock.patch(M_PATH + "UAContractClient")
    def test_user_facing_error_on_machine_token_refresh_failure(
        self, client, get_machine_id, FakeConfig
    ):
        """When attaching, error on failure to refresh the machine token."""

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {
                self.refresh_route: exceptions.UserFacingError(
                    "Machine token refresh fail"
                )
            }
            return fake_client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as exc:
            request_updated_contract(cfg)

        assert "Machine token refresh fail" == str(exc.value)

    @mock.patch("uaclient.entitlements.entitlements_enable_order")
    @mock.patch("uaclient.system.get_machine_id", return_value="mid")
    @mock.patch(M_PATH + "UAContractClient")
    def test_user_facing_error_on_service_token_refresh_failure(
        self, client, get_machine_id, m_enable_order, FakeConfig
    ):
        """When attaching, error on any failed specific service refresh."""

        machine_token = {
            "machineToken": "mToken",
            "machineTokenInfo": {
                "contractInfo": {
                    "id": "cid",
                    "resourceEntitlements": [
                        {"entitled": True, "type": "ent2"},
                        {"entitled": True, "type": "ent1"},
                    ],
                }
            },
        }
        m_enable_order.return_value = ["ent2", "ent1"]

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {self.refresh_route: machine_token}
            return fake_client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine(
            machine_token=machine_token,
        )
        with mock.patch(M_PATH + "process_entitlement_delta") as m_process:
            m_process.side_effect = (
                exceptions.UserFacingError("broken ent1"),
                exceptions.UserFacingError("broken ent2"),
            )
            with pytest.raises(exceptions.UserFacingError) as exc:
                request_updated_contract(cfg)

        assert ATTACH_FAILURE_DEFAULT_SERVICES.msg == str(exc.value.msg)

    @pytest.mark.parametrize(
        "first_error, second_error, ux_error_msg",
        (
            (
                exceptions.UserFacingError(
                    "Ubuntu Pro server provided no aptKey directive for"
                    " esm-infra"
                ),
                (None, False),
                ATTACH_FAILURE_DEFAULT_SERVICES,
            ),
            (RuntimeError("some APT error"), None, UNEXPECTED_ERROR),
            # Order high-priority RuntimeError as second_error to ensure it
            # is raised as primary error_msg
            (
                exceptions.UserFacingError(
                    "Ubuntu Pro server provided no aptKey directive for"
                    " esm-infra"
                ),
                RuntimeError("some APT error"),  # High-priority ordered 2
                UNEXPECTED_ERROR,
            ),
        ),
    )
    @mock.patch("uaclient.entitlements.entitlements_enable_order")
    @mock.patch(M_PATH + "process_entitlement_delta")
    @mock.patch("uaclient.system.get_machine_id", return_value="mid")
    @mock.patch(M_PATH + "UAContractClient")
    def test_user_facing_error_due_to_unexpected_process_entitlement_delta(
        self,
        client,
        get_machine_id,
        process_entitlement_delta,
        m_enable_order,
        first_error,
        second_error,
        ux_error_msg,
        FakeConfig,
    ):
        """Unexpected errors from process_entitlement_delta are raised.

        Remaining entitlements are processed regardless of error and error is
        raised at the end.

        Unexpected exceptions take priority over the handled UserFacingErrors.
        """
        # Fail first and succeed second call to process_entitlement_delta
        process_entitlement_delta.side_effect = (
            first_error,
            second_error,
            (None, False),
        )

        # resourceEntitlements specifically ordered reverse alphabetically
        # to ensure proper sorting for process_contract_delta calls below
        machine_token = {
            "machineToken": "mToken",
            "machineTokenInfo": {
                "contractInfo": {
                    "id": "cid",
                    "resourceEntitlements": [
                        {"entitled": False, "type": "ent3"},
                        {"entitled": False, "type": "ent2"},
                        {"entitled": True, "type": "ent1"},
                    ],
                }
            },
        }
        m_enable_order.return_value = ["ent3", "ent2", "ent1"]

        cfg = FakeConfig.for_attached_machine(
            machine_token=machine_token,
        )
        fake_client = FakeContractClient(cfg)
        fake_client._responses = {
            self.refresh_route: machine_token,
            self.access_route_ent1: {
                "entitlement": {
                    "entitled": True,
                    "type": "ent1",
                    "new": "newval",
                }
            },
        }

        client.return_value = fake_client
        with pytest.raises(exceptions.UserFacingError) as exc:
            assert None is request_updated_contract(cfg)
        assert 3 == process_entitlement_delta.call_count
        assert ux_error_msg.msg == str(exc.value.msg)

    @mock.patch("uaclient.entitlements.entitlements_enable_order")
    @mock.patch(M_PATH + "process_entitlement_delta")
    @mock.patch("uaclient.system.get_machine_id", return_value="mid")
    @mock.patch(M_PATH + "UAContractClient")
    def test_attached_config_refresh_machine_token_and_services(
        self,
        client,
        get_machine_id,
        process_entitlement_delta,
        m_enable_order,
        FakeConfig,
    ):
        """When attached, refresh machine token and entitled services.

        Processing service deltas are processed in a sorted order based on
        service dependencies to ensure operations occur the same regardless
        of dict ordering.
        """
        m_enable_order.return_value = ["ent2", "ent1"]

        machine_token = {
            "machineToken": "mToken",
            "machineTokenInfo": {
                "contractInfo": {
                    "id": "cid",
                    "resourceEntitlements": [
                        {"entitled": False, "type": "ent2"},
                        {"entitled": True, "type": "ent1"},
                    ],
                }
            },
        }
        new_token = copy.deepcopy(machine_token)
        new_token["machineTokenInfo"]["contractInfo"]["resourceEntitlements"][
            1
        ]["new"] = "newval"

        def fake_contract_client(cfg):
            client = FakeContractClient(cfg)
            client._responses = {self.refresh_route: new_token}
            return client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine(
            machine_token=machine_token,
        )
        process_entitlement_delta.return_value = (None, False)
        assert None is request_updated_contract(cfg)
        assert new_token == cfg.machine_token_file.machine_token

        process_calls = [
            mock.call(
                cfg=cfg,
                orig_access={
                    "entitlement": {"entitled": False, "type": "ent2"}
                },
                new_access={
                    "entitlement": {"entitled": False, "type": "ent2"}
                },
                allow_enable=False,
                series_overrides=True,
            ),
            mock.call(
                cfg=cfg,
                orig_access={
                    "entitlement": {"entitled": True, "type": "ent1"}
                },
                new_access={
                    "entitlement": {
                        "entitled": True,
                        "type": "ent1",
                        "new": "newval",
                    }
                },
                allow_enable=False,
                series_overrides=True,
            ),
        ]
        assert process_calls == process_entitlement_delta.call_args_list


@mock.patch("uaclient.contract.UAContractClient.get_updated_contract_info")
class TestContractChanged:
    @pytest.mark.parametrize("has_contract_expired", (False, True))
    def test_contract_change_with_expiry(
        self, get_updated_contract_info, has_contract_expired, FakeConfig
    ):
        if has_contract_expired:
            expiry_date = util.parse_rfc3339_date("2041-05-08T19:02:26Z")
            ret_val = True
        else:
            expiry_date = util.parse_rfc3339_date("2040-05-08T19:02:26Z")
            ret_val = False
        get_updated_contract_info.return_value = {
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
        self, get_updated_contract_info, has_contract_changed, FakeConfig
    ):
        if has_contract_changed:
            resourceEntitlements = [{"type": "token1", "entitled": True}]
            resourceTokens = [{"token": "token1", "type": "resource1"}]
        else:
            resourceTokens = []
            resourceEntitlements = []
        get_updated_contract_info.return_value = {
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
            orig_access["entitlement"].update(
                {
                    "series": {
                        "dontMatch": {
                            "affordances": {
                                "some_affordance": ["ubuntuX-series-overriden"]
                            }
                        }
                    },
                    "overrides": [
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
                    ],
                }
            )

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
                "overrides": [
                    {
                        "selector": {"series": series_selector},
                        "affordances": {
                            "some_affordance": ["series_overriden"]
                        },
                    },
                    {
                        "selector": {"cloud": cloud_selector},
                        "affordances": {
                            "some_affordance": ["cloud_overriden"]
                        },
                    },
                    {
                        "selector": {
                            "series": series_selector,
                            "cloud": series_cloud_selector,
                        },
                        "affordances": {"some_affordance": ["both_overriden"]},
                    },
                ],
            }
        }

        expected = {
            "entitlement": {
                "affordances": {"some_affordance": [expected_value]}
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
                "overrides": [
                    {
                        "selector": {"series": "ubuntuX"},
                        "affordances": {
                            "some_affordance": ["series_overriden"]
                        },
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
                ],
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
            }
        }

        apply_contract_overrides(orig_access)
        assert orig_access == expected


@mock.patch("uaclient.serviceclient.UAServiceClient.request_url")
class TestRequestAutoAttach:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_request_for_invalid_pro_image(
        self, m_request_url, caplog_text, FakeConfig
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
        m_request_url.side_effect = exceptions.ContractAPIError(
            exceptions.UrlError("test", 400),
            error_response=error_response,
        )

        with pytest.raises(exceptions.InvalidProImage) as exc_error:
            contract.request_auto_attach_contract_token(
                instance=mock.MagicMock()
            )

        expected_message = INVALID_PRO_IMAGE.format(
            msg=error_response["message"]
        )
        assert expected_message.msg == exc_error.value.msg
        assert error_response["message"] in caplog_text()
        assert exc_error.value.msg_code == "invalid-pro-image"

import copy
import logging
import socket
from typing import Any, Dict, List, Optional, Tuple

from uaclient import (
    clouds,
    event_logger,
    exceptions,
    http,
    messages,
    system,
    util,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.config import UAConfig
from uaclient.defaults import ATTACH_FAIL_DATE_FORMAT
from uaclient.http import serviceclient

# Here we describe every endpoint from the ua-contracts
# service that is used by this client implementation.
API_V1_ADD_CONTRACT_MACHINE = "/v1/context/machines/token"
API_V1_GET_CONTRACT_MACHINE = (
    "/v1/contracts/{contract}/context/machines/{machine}"
)
API_V1_UPDATE_CONTRACT_MACHINE = (
    "/v1/contracts/{contract}/context/machines/{machine}"
)
API_V1_AVAILABLE_RESOURCES = "/v1/resources"
API_V1_GET_RESOURCE_MACHINE_ACCESS = (
    "/v1/resources/{resource}/context/machines/{machine}"
)
API_V1_GET_CONTRACT_TOKEN_FOR_CLOUD_INSTANCE = "/v1/clouds/{cloud_type}/token"
API_V1_UPDATE_ACTIVITY_TOKEN = (
    "/v1/contracts/{contract}/machine-activity/{machine}"
)
API_V1_GET_CONTRACT_USING_TOKEN = "/v1/contract"

API_V1_GET_MAGIC_ATTACH_TOKEN_INFO = "/v1/magic-attach"
API_V1_NEW_MAGIC_ATTACH = "/v1/magic-attach"
API_V1_REVOKE_MAGIC_ATTACH = "/v1/magic-attach"

OVERRIDE_SELECTOR_WEIGHTS = {
    "series_overrides": 1,
    "series": 2,
    "cloud": 3,
    "variant": 4,
}

event = event_logger.get_event_logger()


class UAContractClient(serviceclient.UAServiceClient):

    cfg_url_base_attr = "contract_url"

    @util.retry(socket.timeout, retry_sleeps=[1, 2, 2])
    def add_contract_machine(self, contract_token, machine_id=None):
        """Requests machine attach to the provided machine_id.

        @param contract_token: Token string providing authentication to
            ContractBearer service endpoint.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing the machine-token.
        """
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(contract_token)})
        data = self._get_platform_data(machine_id)
        response = self.request_url(
            API_V1_ADD_CONTRACT_MACHINE, data=data, headers=headers
        )
        if response.code == 401:
            raise exceptions.AttachInvalidTokenError()
        elif response.code == 403:
            msg = _create_attach_forbidden_message(response)
            raise exceptions.UserFacingError(
                msg=msg.msg,
                msg_code=msg.name,
                additional_info=msg.additional_info,
            )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                API_V1_ADD_CONTRACT_MACHINE, response.code, response.body
            )

        self.cfg.machine_token_file.write(response.json_dict)

        system.get_machine_id.cache_clear()
        machine_id = response.json_dict.get("machineTokenInfo", {}).get(
            "machineId", data.get("machineId")
        )
        self.cfg.write_cache("machine-id", machine_id)

        return response.json_dict

    def available_resources(self) -> Dict[str, Any]:
        """Requests list of entitlements available to this machine type."""
        response = self.request_url(
            API_V1_AVAILABLE_RESOURCES,
            query_params=self._get_platform_basic_info(),
        )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                API_V1_AVAILABLE_RESOURCES, response.code, response.body
            )
        return response.json_dict

    def get_contract_using_token(self, contract_token: str) -> Dict[str, Any]:
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(contract_token)})
        response = self.request_url(
            API_V1_GET_CONTRACT_USING_TOKEN, headers=headers
        )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                API_V1_GET_CONTRACT_USING_TOKEN, response.code, response.body
            )
        return response.json_dict

    @util.retry(socket.timeout, retry_sleeps=[1, 2, 2])
    def get_contract_token_for_cloud_instance(
        self, *, instance: clouds.AutoAttachCloudInstance
    ):
        """Requests contract token for auto-attach images for Pro clouds.

        @param instance: AutoAttachCloudInstance for the cloud.

        @return: Dict of the JSON response containing the contract-token.
        """
        response = self.request_url(
            API_V1_GET_CONTRACT_TOKEN_FOR_CLOUD_INSTANCE.format(
                cloud_type=instance.cloud_type
            ),
            data=instance.identity_doc,
        )
        if response.code != 200:
            msg = response.json_dict.get("message", "")
            if msg:
                logging.debug(msg)
                raise exceptions.InvalidProImage(error_msg=msg)
            raise exceptions.ContractAPIError(
                API_V1_GET_CONTRACT_TOKEN_FOR_CLOUD_INSTANCE,
                response.code,
                response.body,
            )

        self.cfg.write_cache("contract-token", response.json_dict)
        return response.json_dict

    def get_resource_machine_access(
        self,
        machine_token: str,
        resource: str,
        machine_id: Optional[str] = None,
        save_file: bool = True,
    ) -> Dict[str, Any]:
        """Requests machine access context for a given resource

        @param machine_token: The authentication token needed to talk to
            this contract service endpoint.
        @param resource: Entitlement name.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.
        @save_file: If the machine access should be saved on the user machine

        @return: Dict of the JSON response containing entitlement accessInfo.
        """
        if not machine_id:
            machine_id = system.get_machine_id(self.cfg)
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        url = API_V1_GET_RESOURCE_MACHINE_ACCESS.format(
            resource=resource, machine=machine_id
        )
        response = self.request_url(url, headers=headers)
        if response.code != 200:
            raise exceptions.ContractAPIError(
                API_V1_GET_RESOURCE_MACHINE_ACCESS,
                response.code,
                response.body,
            )
        if response.headers.get("expires"):
            response.json_dict["expires"] = response.headers["expires"]
        if save_file:
            self.cfg.write_cache(
                "machine-access-{}".format(resource), response.json_dict
            )
        return response.json_dict

    def update_contract_machine(
        self,
        machine_token: str,
        contract_id: str,
        machine_id: Optional[str] = None,
    ) -> Dict:
        """Update existing machine-token for an attached machine."""
        return self._update_contract_machine(
            machine_token=machine_token,
            contract_id=contract_id,
            machine_id=machine_id,
        )

    def update_activity_token(self):
        """Report current activity token and enabled services.

        This will report to the contracts backend all the current
        enabled services in the system.
        """
        contract_id = self.cfg.machine_token_file.contract_id
        machine_token = self.cfg.machine_token.get("machineToken")
        machine_id = system.get_machine_id(self.cfg)

        request_data = self._get_activity_info(machine_id)
        url = API_V1_UPDATE_ACTIVITY_TOKEN.format(
            contract=contract_id, machine=machine_id
        )
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})

        response = self.request_url(url, headers=headers, data=request_data)
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url, response.code, response.body
            )

        # We will update the `machine-token.json` based on the response
        # provided by the server. We expect the response to be
        # a full `activityInfo` object which belongs at the root of
        # `machine-token.json`
        if response.json_dict:

            machine_token = self.cfg.machine_token
            # The activity information received as a response here
            # will not provide the information inside an activityInfo
            # structure. However, this structure will be reflected when
            # we reach the contract for attach and refresh requests.
            # Because of that, we will store the response directly on
            # the activityInfo key
            machine_token["activityInfo"] = response.json_dict
            self.cfg.machine_token_file.write(machine_token)

    def get_magic_attach_token_info(self, magic_token: str) -> Dict[str, Any]:
        """Request magic attach token info.

        When the magic token is registered, it will contain new fields
        that will allow us to know that the attach process can proceed
        """
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(magic_token)})

        try:
            response = self.request_url(
                API_V1_GET_MAGIC_ATTACH_TOKEN_INFO, headers=headers
            )
        except exceptions.UrlError as e:
            logging.exception(str(e))
            raise exceptions.ConnectivityError()
        if response.code == 401:
            raise exceptions.MagicAttachTokenError()
        if response.code == 503:
            raise exceptions.MagicAttachUnavailable()
        if response.code != 200:
            raise exceptions.ContractAPIError(
                API_V1_GET_MAGIC_ATTACH_TOKEN_INFO,
                response.code,
                response.body,
            )

        return response.json_dict

    def new_magic_attach_token(self) -> Dict[str, Any]:
        """Create a magic attach token for the user."""
        headers = self.headers()

        try:
            response = self.request_url(
                API_V1_NEW_MAGIC_ATTACH,
                headers=headers,
                method="POST",
            )
        except exceptions.UrlError as e:
            logging.exception(str(e))
            raise exceptions.ConnectivityError()
        if response.code == 503:
            raise exceptions.MagicAttachUnavailable()
        if response.code != 200:
            raise exceptions.ContractAPIError(
                API_V1_NEW_MAGIC_ATTACH, response.code, response.body
            )

        return response.json_dict

    def revoke_magic_attach_token(self, magic_token: str):
        """Revoke a magic attach token for the user."""
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(magic_token)})

        try:
            response = self.request_url(
                API_V1_REVOKE_MAGIC_ATTACH,
                headers=headers,
                method="DELETE",
            )
        except exceptions.UrlError as e:
            logging.exception(str(e))
            raise exceptions.ConnectivityError()
        if response.code == 400:
            raise exceptions.MagicAttachTokenAlreadyActivated()
        if response.code == 401:
            raise exceptions.MagicAttachTokenError()
        if response.code == 503:
            raise exceptions.MagicAttachUnavailable()
        if response.code != 200:
            raise exceptions.ContractAPIError(
                API_V1_REVOKE_MAGIC_ATTACH, response.code, response.body
            )

    def get_contract_machine(
        self,
        machine_token: str,
        contract_id: str,
        machine_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get the updated machine token from the contract server.

        @param machine_token: The machine token needed to talk to
            this contract service endpoint.
        @param contract_id: Unique contract id provided by contract service
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.
        """
        if not machine_id:
            machine_id = self._get_platform_data(machine_id).get(
                "machineId", None
            )
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        url = API_V1_GET_CONTRACT_MACHINE.format(
            contract=contract_id,
            machine=machine_id,
        )
        response = self.request_url(
            url,
            method="GET",
            headers=headers,
            query_params=self._get_platform_basic_info(),
        )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url, response.code, response.body
            )
        if response.headers.get("expires"):
            response.json_dict["expires"] = response.headers["expires"]
        return response.json_dict

    def _update_contract_machine(
        self,
        machine_token: str,
        contract_id: str,
        machine_id: Optional[str] = None,
    ) -> Dict:
        """Request machine token refresh from contract server.

        @param machine_token: The machine token needed to talk to
            this contract service endpoint.
        @param contract_id: Unique contract id provided by contract service.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing refreshed machine-token
        """
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        data = self._get_platform_data(machine_id)
        data["activityInfo"] = self._get_activity_info()
        url = API_V1_UPDATE_CONTRACT_MACHINE.format(
            contract=contract_id, machine=data["machineId"]
        )
        response = self.request_url(
            url, headers=headers, method="POST", data=data
        )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url, response.code, response.body
            )
        if response.headers.get("expires"):
            response.json_dict["expires"] = response.headers["expires"]
        machine_id = response.json_dict.get("machineTokenInfo", {}).get(
            "machineId", data.get("machineId")
        )
        return response.json_dict

    def update_files_after_machine_token_update(
        self, response: Dict[str, Any]
    ):
        self.cfg.machine_token_file.write(response)
        system.get_machine_id.cache_clear()
        data = self._get_platform_data(None)
        machine_id = response.get("machineTokenInfo", {}).get(
            "machineId", data.get("machineId")
        )
        self.cfg.write_cache("machine-id", machine_id)

    def _get_platform_data(self, machine_id):
        """Return a dict of platform-related data for contract requests"""
        if not machine_id:
            machine_id = system.get_machine_id(self.cfg)
        return {
            "machineId": machine_id,
            "architecture": system.get_dpkg_arch(),
            "os": {
                "type": "Linux",
                "distribution": system.get_release_info().distribution,
                "release": system.get_release_info().release,
                "series": system.get_release_info().series,
                "version": system.get_release_info().pretty_version,
                "kernel": system.get_kernel_info().uname_release,
                "virt": system.get_virt_type(),
            },
        }

    def _get_platform_basic_info(self):
        """Return a dict of platform basic info for some contract requests"""
        return {
            "architecture": system.get_dpkg_arch(),
            "series": system.get_release_info().series,
            "kernel": system.get_kernel_info().uname_release,
            "virt": system.get_virt_type(),
        }

    def _get_activity_info(self, machine_id: Optional[str] = None):
        """Return a dict of activity info data for contract requests"""
        if not machine_id:
            machine_id = system.get_machine_id(self.cfg)

        # If the activityID is null we should provide the endpoint
        # with the instance machine id as the activityID
        activity_id = self.cfg.machine_token_file.activity_id or machine_id
        enabled_services = _enabled_services(self.cfg).enabled_services or []

        return {
            "activityID": activity_id,
            "activityToken": self.cfg.machine_token_file.activity_token,
            "resources": [service.name for service in enabled_services],
        }


def process_entitlements_delta(
    cfg: UAConfig,
    past_entitlements: Dict[str, Any],
    new_entitlements: Dict[str, Any],
    allow_enable: bool,
    series_overrides: bool = True,
) -> None:
    """Iterate over all entitlements in new_entitlement and apply any delta
    found according to past_entitlements.

    :param cfg: UAConfig instance
    :param past_entitlements: dict containing the last valid information
        regarding service entitlements.
    :param new_entitlements: dict containing the current information regarding
        service entitlements.
    :param allow_enable: Boolean set True if allowed to perform the enable
        operation. When False, a message will be logged to inform the user
        about the recommended enabled service.
    :param series_overrides: Boolean set True if series overrides should be
        applied to the new_access dict.
    """
    from uaclient.actions import enable_entitlements_by_name
    from uaclient.entitlements import entitlements_enable_order

    delta_error = False
    unexpected_error = False

    failed_services = []  # type: List[str]
    services_to_enable = []  # type: List[str]
    # We need to sort our entitlements because some of them
    # depend on other service to be enable first.
    for name in entitlements_enable_order(cfg):
        try:
            new_entitlement = new_entitlements[name]
        except KeyError:
            continue

        failed_services = []
        try:
            (
                deltas,
                service_enabled,
                svcs_to_enable,
            ) = process_entitlement_delta(
                cfg=cfg,
                orig_access=past_entitlements.get(name, {}),
                new_access=new_entitlement,
                allow_enable=allow_enable,
                series_overrides=series_overrides,
            )
        except exceptions.UserFacingError:
            delta_error = True
            failed_services.append(name)
            with util.disable_log_to_console():
                logging.error(
                    "Failed to process contract delta for {name}:"
                    " {delta}".format(name=name, delta=new_entitlement)
                )
        except Exception:
            unexpected_error = True
            failed_services.append(name)
            with util.disable_log_to_console():
                logging.exception(
                    "Unexpected error processing contract delta for {name}:"
                    " {delta}".format(name=name, delta=new_entitlement)
                )
        else:
            # If we have any deltas to process and we were able to process
            # them, then we will mark that service as successfully enabled
            if service_enabled and deltas:
                event.service_processed(name)
            services_to_enable.extend(svcs_to_enable)

    for name, ent_ret, reason, ex in enable_entitlements_by_name(
        cfg,
        services_to_enable,
        assume_yes=True,
        allow_beta=True,
    ):
        # TODO: error handling
        pass

    event.services_failed(failed_services)
    if unexpected_error:
        raise exceptions.AttachFailureUnknownError(
            failed_services=[
                (name, messages.UNEXPECTED_ERROR) for name in failed_services
            ]
        )
    elif delta_error:
        raise exceptions.AttachFailureDefaultServices(
            failed_services=[
                (name, messages.ATTACH_FAILURE_DEFAULT_SERVICES)
                for name in failed_services
            ]
        )


def process_entitlement_delta(
    cfg: UAConfig,
    orig_access: Dict[str, Any],
    new_access: Dict[str, Any],
    allow_enable: bool = False,
    series_overrides: bool = True,
) -> Tuple[Dict, bool, List[str]]:
    """Process a entitlement access dictionary deltas if they exist.

    :param cfg: UAConfig instance
    :param orig_access: Dict with original entitlement access details before
        contract refresh deltas
    :param new_access: Dict with updated entitlement access details after
        contract refresh
    :param allow_enable: Boolean set True if allowed to perform the enable
        operation. When False, a message will be logged to inform the user
        about the recommended enabled service.
    :param series_overrides: Boolean set True if series overrides should be
        applied to the new_access dict.

    :raise UserFacingError: on failure to process deltas.
    :return: A tuple containing
        dict of processed deltas
        boolean indicating if the service was fully processed
    """
    from uaclient.entitlements import entitlement_factory

    if series_overrides:
        apply_contract_overrides(new_access)

    svcs_to_enable = []
    deltas = util.get_dict_deltas(orig_access, new_access)
    ret = False
    entitlement = None
    if deltas:
        name = orig_access.get("entitlement", {}).get("type")
        if not name:
            name = deltas.get("entitlement", {}).get("type")
        if not name:
            msg = messages.INVALID_CONTRACT_DELTAS_SERVICE_TYPE.format(
                orig=orig_access, new=new_access
            )
            raise exceptions.UserFacingError(msg=msg.msg, msg_code=msg.name)

        variant = (
            new_access.get("entitlements", {})
            .get("obligations", {})
            .get("use_selector", "")
        )
        try:
            ent_cls = entitlement_factory(cfg=cfg, name=name, variant=variant)
        except exceptions.EntitlementNotFoundError as exc:
            logging.debug(
                'Skipping entitlement deltas for "%s". No such class', name
            )
            raise exc

        entitlement = ent_cls(cfg=cfg, assume_yes=allow_enable)
        ret, svcs_to_enable = entitlement.process_contract_deltas(
            orig_access, deltas, allow_enable=allow_enable
        )
    return deltas, ret, svcs_to_enable


def _create_attach_forbidden_message(
    response: http.HTTPResponse,
) -> messages.NamedMessage:
    msg = messages.ATTACH_EXPIRED_TOKEN
    info = response.json_dict.get("info")
    if info:
        contract_id = info["contractId"]
        reason = info["reason"]
        reason_msg = None

        if reason == "no-longer-effective":
            date = info["time"].strftime(ATTACH_FAIL_DATE_FORMAT)
            additional_info = {
                "contract_expiry_date": info["time"].strftime("%m-%d-%Y"),
                "contract_id": contract_id,
            }
            reason_msg = messages.ATTACH_FORBIDDEN_EXPIRED.format(
                contract_id=contract_id, date=date
            )
            reason_msg.additional_info = additional_info
        elif reason == "not-effective-yet":
            date = info["time"].strftime(ATTACH_FAIL_DATE_FORMAT)
            additional_info = {
                "contract_effective_date": info["time"].strftime("%m-%d-%Y"),
                "contract_id": contract_id,
            }
            reason_msg = messages.ATTACH_FORBIDDEN_NOT_YET.format(
                contract_id=contract_id, date=date
            )
            reason_msg.additional_info = additional_info
        elif reason == "never-effective":
            reason_msg = messages.ATTACH_FORBIDDEN_NEVER.format(
                contract_id=contract_id
            )

        if reason_msg:
            msg = messages.ATTACH_FORBIDDEN.format(reason=reason_msg.msg)
            msg.name = reason_msg.name
            msg.additional_info = reason_msg.additional_info

    return msg


def request_updated_contract(
    cfg, contract_token: Optional[str] = None, allow_enable=False
):
    """Request contract refresh from ua-contracts service.

    Compare original token to new token and react to entitlement deltas.

    :param cfg: Instance of UAConfig for this machine.
    :param contract_token: String contraining an optional contract token.
    :param allow_enable: Boolean set True if allowed to perform the enable
        operation. When False, a message will be logged to inform the user
        about the recommended enabled service.

    :raise UserFacingError: on failure to update contract or error processing
        contract deltas
    :raise ConnectivityError: On failure to contact the server
    """
    orig_token = cfg.machine_token
    orig_entitlements = cfg.machine_token_file.entitlements
    if orig_token and contract_token:
        msg = messages.UNEXPECTED_CONTRACT_TOKEN_ON_ATTACHED_MACHINE
        raise exceptions.UserFacingError(msg=msg.msg, msg_code=msg.name)
    contract_client = UAContractClient(cfg)
    if contract_token:  # We are a mid ua-attach and need to get machinetoken
        try:
            contract_client.add_contract_machine(contract_token=contract_token)
        except exceptions.UrlError as e:
            with util.disable_log_to_console():
                logging.exception(str(e))
            raise exceptions.ConnectivityError()
    else:
        machine_token = orig_token["machineToken"]
        contract_id = orig_token["machineTokenInfo"]["contractInfo"]["id"]
        resp = contract_client.update_contract_machine(
            machine_token=machine_token, contract_id=contract_id
        )
        contract_client.update_files_after_machine_token_update(resp)

    process_entitlements_delta(
        cfg,
        orig_entitlements,
        cfg.machine_token_file.entitlements,
        allow_enable,
    )


def get_available_resources(cfg: UAConfig) -> List[Dict]:
    """Query available resources from the contract server for this machine."""
    client = UAContractClient(cfg)
    resources = client.available_resources()
    return resources.get("resources", [])


def get_contract_information(cfg: UAConfig, token: str) -> Dict[str, Any]:
    """Query contract information for a specific token"""
    client = UAContractClient(cfg)
    return client.get_contract_using_token(token)


def is_contract_changed(cfg: UAConfig) -> bool:
    orig_token = cfg.machine_token
    orig_entitlements = cfg.machine_token_file.entitlements
    machine_token = orig_token.get("machineToken", "")
    contract_id = (
        orig_token.get("machineTokenInfo", {})
        .get("contractInfo", {})
        .get("id", None)
    )
    if not contract_id:
        return False

    contract_client = UAContractClient(cfg)
    resp = contract_client.get_contract_machine(machine_token, contract_id)
    resp_expiry = (
        resp.get("machineTokenInfo", {})
        .get("contractInfo", {})
        .get("effectiveTo", None)
    )
    new_expiry = (
        resp_expiry
        if resp_expiry
        else cfg.machine_token_file.contract_expiry_datetime
    )
    if cfg.machine_token_file.contract_expiry_datetime != new_expiry:
        return True
    curr_entitlements = cfg.machine_token_file.get_entitlements_from_token(
        resp
    )
    for name, new_entitlement in sorted(curr_entitlements.items()):
        deltas = util.get_dict_deltas(
            orig_entitlements.get(name, {}), new_entitlement
        )
        if deltas:
            return True
    return False


def _get_override_weight(
    override_selector: Dict[str, str], selector_values: Dict[str, str]
) -> int:
    override_weight = 0
    for selector, value in override_selector.items():
        if (selector, value) not in selector_values.items():
            return 0
        override_weight += OVERRIDE_SELECTOR_WEIGHTS[selector]

    return override_weight


def _select_overrides(
    entitlement: Dict[str, Any],
    series_name: str,
    cloud_type: str,
    variant: Optional[str] = None,
) -> Dict[int, Dict[str, Any]]:
    overrides = {}

    selector_values = {"series": series_name, "cloud": cloud_type}
    if variant:
        selector_values["variant"] = variant

    series_overrides = entitlement.pop("series", {}).pop(series_name, {})
    if series_overrides:
        overrides[
            OVERRIDE_SELECTOR_WEIGHTS["series_overrides"]
        ] = series_overrides

    general_overrides = copy.deepcopy(entitlement.get("overrides", []))
    for override in general_overrides:
        weight = _get_override_weight(
            override.pop("selector"), selector_values
        )
        if weight:
            overrides[weight] = override

    return overrides


def apply_contract_overrides(
    orig_access: Dict[str, Any],
    series: Optional[str] = None,
    variant: Optional[str] = None,
) -> None:
    """Apply series-specific overrides to an entitlement dict.

    This function mutates orig_access dict by applying any series-overrides to
    the top-level keys under 'entitlement'. The series-overrides are sparse
    and intended to supplement existing top-level dict values. So, sub-keys
    under the top-level directives, obligations and affordance sub-key values
    will be preserved if unspecified in series-overrides.

    To more clearly indicate that orig_access in memory has already had
    the overrides applied, the 'series' key is also removed from the
    orig_access dict.

    :param orig_access: Dict with original entitlement access details
    """
    from uaclient.clouds.identity import get_cloud_type

    if not all([isinstance(orig_access, dict), "entitlement" in orig_access]):
        raise RuntimeError(
            'Expected entitlement access dict. Missing "entitlement" key:'
            " {}".format(orig_access)
        )

    series_name = (
        system.get_release_info().series if series is None else series
    )
    cloud_type, _ = get_cloud_type()
    orig_entitlement = orig_access.get("entitlement", {})

    overrides = _select_overrides(
        orig_entitlement, series_name, cloud_type, variant
    )

    for _weight, overrides_to_apply in sorted(overrides.items()):
        for key, value in overrides_to_apply.items():
            current = orig_access["entitlement"].get(key)
            if isinstance(current, dict):
                # If the key already exists and is a dict,
                # update that dict using the override
                current.update(value)
            else:
                # Otherwise, replace it wholesale
                orig_access["entitlement"][key] = value

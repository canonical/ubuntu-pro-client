import copy
import logging
import socket
from collections import namedtuple
from typing import Any, Dict, List, Optional, Tuple

import uaclient.files.machine_token as mtf
from uaclient import (
    clouds,
    event_logger,
    exceptions,
    http,
    messages,
    secret_manager,
    system,
    util,
    version,
)
from uaclient.api.u.pro.status.enabled_services.v1 import _enabled_services
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.defaults import ATTACH_FAIL_DATE_FORMAT
from uaclient.files.state_files import attachment_data_file, machine_id_file
from uaclient.http import serviceclient
from uaclient.log import get_user_or_root_log_file_path

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
LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


EnableByDefaultService = namedtuple(
    "EnableByDefaultService", ["name", "variant"]
)


class UAContractClient(serviceclient.UAServiceClient):
    cfg_url_base_attr = "contract_url"

    def __init__(
        self,
        cfg: Optional[UAConfig] = None,
    ) -> None:
        super().__init__(cfg=cfg)
        self.machine_token_file = mtf.get_machine_token_file()

    @util.retry(socket.timeout, retry_sleeps=[1, 2, 2])
    def add_contract_machine(
        self, contract_token, attachment_dt, machine_id=None
    ):
        """Requests machine attach to the provided machine_id.

        @param contract_token: Token string providing authentication to
            ContractBearer service endpoint.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing the machine-token.
        """
        if not machine_id:
            machine_id = system.get_machine_id(self.cfg)

        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(contract_token)})
        activity_info = self._get_activity_info()
        activity_info["lastAttachment"] = attachment_dt.isoformat()
        data = {"machineId": machine_id, "activityInfo": activity_info}
        backcompat_data = _support_old_machine_info(data)
        response = self.request_url(
            API_V1_ADD_CONTRACT_MACHINE, data=backcompat_data, headers=headers
        )
        if response.code == 401:
            raise exceptions.AttachInvalidTokenError()
        elif response.code == 403:
            _raise_attach_forbidden_message(response)
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=API_V1_ADD_CONTRACT_MACHINE,
                code=response.code,
                body=response.body,
            )
        response_json = response.json_dict
        secret_manager.secrets.add_secret(
            response_json.get("machineToken", "")
        )
        for token in response_json.get("resourceTokens", []):
            secret_manager.secrets.add_secret(token.get("token", ""))
        return response_json

    def available_resources(self) -> Dict[str, Any]:
        """Requests list of entitlements available to this machine type."""
        activity_info = self._get_activity_info()
        response = self.request_url(
            API_V1_AVAILABLE_RESOURCES,
            query_params={
                "architecture": activity_info["architecture"],
                "series": activity_info["series"],
                "kernel": activity_info["kernel"],
                "virt": activity_info["virt"],
            },
        )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=API_V1_AVAILABLE_RESOURCES,
                code=response.code,
                body=response.body,
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
                url=API_V1_GET_CONTRACT_USING_TOKEN,
                code=response.code,
                body=response.body,
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
                LOG.debug(msg)
                raise exceptions.InvalidProImage(error_msg=msg)
            raise exceptions.ContractAPIError(
                url=API_V1_GET_CONTRACT_TOKEN_FOR_CLOUD_INSTANCE,
                code=response.code,
                body=response.body,
            )

        response_json = response.json_dict
        secret_manager.secrets.add_secret(
            response_json.get("contractToken", "")
        )
        return response_json

    def get_resource_machine_access(
        self,
        machine_token: str,
        resource: str,
        machine_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Requests machine access context for a given resource

        @param machine_token: The authentication token needed to talk to
            this contract service endpoint.
        @param resource: Entitlement name.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

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
                url=API_V1_GET_RESOURCE_MACHINE_ACCESS,
                code=response.code,
                body=response.body,
            )
        if response.headers.get("expires"):
            response.json_dict["expires"] = response.headers["expires"]

        response_json = response.json_dict
        for token in response_json.get("resourceTokens", []):
            secret_manager.secrets.add_secret(token.get("token", ""))
        return response_json

    def update_activity_token(self):
        """Report current activity token and enabled services.

        This will report to the contracts backend all the current
        enabled services in the system.
        """
        contract_id = self.machine_token_file.contract_id
        machine_token = self.machine_token_file.machine_token.get(
            "machineToken"
        )
        machine_id = system.get_machine_id(self.cfg)

        request_data = self._get_activity_info()
        url = API_V1_UPDATE_ACTIVITY_TOKEN.format(
            contract=contract_id, machine=machine_id
        )
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})

        response = self.request_url(url, headers=headers, data=request_data)
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=url, code=response.code, body=response.body
            )

        # We will update the `machine-token.json` based on the response
        # provided by the server. We expect the response to be
        # a full `activityInfo` object which belongs at the root of
        # `machine-token.json`
        if response.json_dict:
            machine_token = self.machine_token_file.machine_token
            # The activity information received as a response here
            # will not provide the information inside an activityInfo
            # structure. However, this structure will be reflected when
            # we reach the contract for attach and refresh requests.
            # Because of that, we will store the response directly on
            # the activityInfo key
            machine_token["activityInfo"] = response.json_dict
            self.machine_token_file.write(machine_token)

    def get_magic_attach_token_info(self, magic_token: str) -> Dict[str, Any]:
        """Request magic attach token info.

        When the magic token is registered, it will contain new fields
        that will allow us to know that the attach process can proceed
        """
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(magic_token)})
        response = self.request_url(
            API_V1_GET_MAGIC_ATTACH_TOKEN_INFO, headers=headers
        )

        if response.code == 401:
            raise exceptions.MagicAttachTokenError()
        if response.code == 503:
            raise exceptions.MagicAttachUnavailable()
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=API_V1_GET_MAGIC_ATTACH_TOKEN_INFO,
                code=response.code,
                body=response.body,
            )
        response_json = response.json_dict
        secret_fields = ["token", "userCode", "contractToken"]
        for field in secret_fields:
            secret_manager.secrets.add_secret(response_json.get(field, ""))
        return response_json

    def new_magic_attach_token(self) -> Dict[str, Any]:
        """Create a magic attach token for the user."""
        headers = self.headers()
        response = self.request_url(
            API_V1_NEW_MAGIC_ATTACH,
            headers=headers,
            method="POST",
        )

        if response.code == 503:
            raise exceptions.MagicAttachUnavailable()
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=API_V1_NEW_MAGIC_ATTACH,
                code=response.code,
                body=response.body,
            )
        response_json = response.json_dict
        secret_fields = ["token", "userCode", "contractToken"]
        for field in secret_fields:
            secret_manager.secrets.add_secret(response_json.get(field, ""))
        return response_json

    def revoke_magic_attach_token(self, magic_token: str):
        """Revoke a magic attach token for the user."""
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(magic_token)})
        response = self.request_url(
            API_V1_REVOKE_MAGIC_ATTACH,
            headers=headers,
            method="DELETE",
        )

        if response.code == 400:
            raise exceptions.MagicAttachTokenAlreadyActivated()
        if response.code == 401:
            raise exceptions.MagicAttachTokenError()
        if response.code == 503:
            raise exceptions.MagicAttachUnavailable()
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=API_V1_REVOKE_MAGIC_ATTACH,
                code=response.code,
                body=response.body,
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
            machine_id = system.get_machine_id(self.cfg)

        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        url = API_V1_GET_CONTRACT_MACHINE.format(
            contract=contract_id,
            machine=machine_id,
        )
        activity_info = self._get_activity_info()
        response = self.request_url(
            url,
            method="GET",
            headers=headers,
            query_params={
                "architecture": activity_info["architecture"],
                "series": activity_info["series"],
                "kernel": activity_info["kernel"],
                "virt": activity_info["virt"],
            },
        )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=url, code=response.code, body=response.body
            )
        if response.headers.get("expires"):
            response.json_dict["expires"] = response.headers["expires"]
        return response.json_dict

    def update_contract_machine(
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
        if not machine_id:
            machine_id = system.get_machine_id(self.cfg)

        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        data = {
            "machineId": machine_id,
            "activityInfo": self._get_activity_info(),
        }
        backcompat_data = _support_old_machine_info(data)
        url = API_V1_UPDATE_CONTRACT_MACHINE.format(
            contract=contract_id, machine=machine_id
        )
        response = self.request_url(
            url, headers=headers, method="POST", data=backcompat_data
        )
        if response.code != 200:
            raise exceptions.ContractAPIError(
                url=url, code=response.code, body=response.body
            )
        if response.headers.get("expires"):
            response.json_dict["expires"] = response.headers["expires"]
        return response.json_dict

    def _get_activity_info(self):
        """Return a dict of activity info data for contract requests"""

        machine_info = {
            "distribution": system.get_release_info().distribution,
            "kernel": system.get_kernel_info().uname_release,
            "series": system.get_release_info().series,
            "architecture": system.get_dpkg_arch(),
            "desktop": system.is_desktop(),
            "virt": system.get_virt_type(),
            "clientVersion": version.get_version(),
        }

        if _is_attached(self.cfg).is_attached:
            enabled_services = _enabled_services(self.cfg).enabled_services
            attachment_data = attachment_data_file.read()
            activity_info = {
                "activityID": self.machine_token_file.activity_id
                or system.get_machine_id(self.cfg),
                "activityToken": self.machine_token_file.activity_token,
                "resources": [service.name for service in enabled_services],
                "resourceVariants": {
                    service.name: service.variant_name
                    for service in enabled_services
                    if service.variant_enabled
                },
                "lastAttachment": (
                    attachment_data.attached_at.isoformat()
                    if attachment_data
                    else None
                ),
            }
        else:
            activity_info = {}

        return {
            **activity_info,
            **machine_info,
        }


def _support_old_machine_info(request_body: dict):
    """
    Transforms a request_body that has the new activity_info into a body that
    includes both old and new forms of machineInfo/activityInfo

    This is necessary because there may be old ua-airgapped contract
    servers deployed that we need to support.
    This function is used for attach and refresh calls.
    """
    activity_info = request_body.get("activityInfo", {})

    return {
        "machineId": request_body.get("machineId"),
        "activityInfo": activity_info,
        "architecture": activity_info.get("architecture"),
        "os": {
            "distribution": activity_info.get("distribution"),
            "kernel": activity_info.get("kernel"),
            "series": activity_info.get("series"),
            # These two are required for old ua-airgapped but not sent anymore
            # in the new activityInfo
            "type": "Linux",
            "release": system.get_release_info().release,
        },
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
    from uaclient.entitlements import entitlements_enable_order

    delta_error = False
    unexpected_errors = []

    # We need to sort our entitlements because some of them
    # depend on other service to be enable first.
    failed_services = []  # type: List[str]
    for name in entitlements_enable_order(cfg):
        try:
            new_entitlement = new_entitlements[name]
        except KeyError:
            continue

        failed_services = []
        try:
            deltas, service_enabled = process_entitlement_delta(
                cfg=cfg,
                orig_access=past_entitlements.get(name, {}),
                new_access=new_entitlement,
                allow_enable=allow_enable,
                series_overrides=series_overrides,
            )
        except exceptions.UbuntuProError as e:
            LOG.exception(e)
            delta_error = True
            failed_services.append(name)
            LOG.error(
                "Failed to process contract delta for %s: %r",
                name,
                new_entitlement,
            )
        except Exception as e:
            LOG.exception(e)
            unexpected_errors.append(e)
            failed_services.append(name)
            LOG.exception(
                "Unexpected error processing contract delta for %s: %r",
                name,
                new_entitlement,
            )
        else:
            # If we have any deltas to process and we were able to process
            # them, then we will mark that service as successfully enabled
            if service_enabled and deltas:
                event.service_processed(name)
    event.services_failed(failed_services)
    if len(unexpected_errors) > 0:
        raise exceptions.AttachFailureUnknownError(
            failed_services=[
                (
                    name,
                    messages.UNEXPECTED_ERROR.format(
                        error_msg=str(exception),
                        log_path=get_user_or_root_log_file_path(),
                    ),
                )
                for name, exception in zip(failed_services, unexpected_errors)
            ]
        )
    elif delta_error:
        raise exceptions.AttachFailureDefaultServices(
            failed_services=[
                (name, messages.E_ATTACH_FAILURE_DEFAULT_SERVICES)
                for name in failed_services
            ]
        )


def process_entitlement_delta(
    cfg: UAConfig,
    orig_access: Dict[str, Any],
    new_access: Dict[str, Any],
    allow_enable: bool = False,
    series_overrides: bool = True,
) -> Tuple[Dict, bool]:
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

    :raise UbuntuProError: on failure to process deltas.
    :return: A tuple containing a dict of processed deltas and a
             boolean indicating if the service was fully processed
    """
    from uaclient.entitlements import entitlement_factory

    if series_overrides:
        apply_contract_overrides(new_access)

    deltas = util.get_dict_deltas(orig_access, new_access)
    ret = False
    if deltas:
        name = orig_access.get("entitlement", {}).get("type")
        if not name:
            name = deltas.get("entitlement", {}).get("type")
        if not name:
            raise exceptions.InvalidContractDeltasServiceType(
                orig=orig_access, new=new_access
            )

        variant = (
            new_access.get("entitlements", {})
            .get("obligations", {})
            .get("use_selector", "")
        )
        try:
            entitlement = entitlement_factory(
                cfg=cfg,
                name=name,
                variant=variant,
            )
        except exceptions.EntitlementNotFoundError as exc:
            LOG.debug(
                'Skipping entitlement deltas for "%s". No such class', name
            )
            raise exc

        ret = entitlement.process_contract_deltas(
            orig_access, deltas, allow_enable=allow_enable
        )
    return deltas, ret


def _raise_attach_forbidden_message(
    response: http.HTTPResponse,
) -> messages.NamedMessage:
    info = response.json_dict.get("info")
    if info:
        contract_id = info["contractId"]
        reason = info["reason"]
        if reason == "no-longer-effective":
            date = info["time"].strftime(ATTACH_FAIL_DATE_FORMAT)
            raise exceptions.AttachForbiddenExpired(
                contract_id=contract_id,
                date=date,
                # keep this extra date for backwards compat
                contract_expiry_date=info["time"].strftime("%m-%d-%Y"),
            )
        elif reason == "not-effective-yet":
            date = info["time"].strftime(ATTACH_FAIL_DATE_FORMAT)
            raise exceptions.AttachForbiddenNotYet(
                contract_id=contract_id,
                date=date,
                # keep this extra date for backwards compat
                contract_effective_date=info["time"].strftime("%m-%d-%Y"),
            )
        elif reason == "never-effective":
            raise exceptions.AttachForbiddenNever(contract_id=contract_id)

    raise exceptions.AttachExpiredToken()


def refresh(cfg: UAConfig):
    """Request contract refresh from ua-contracts service.

    :raise UbuntuProError: on failure to update contract or error processing
        contract deltas
    :raise ConnectivityError: On failure during a connection
    """
    machine_token_file = mtf.get_machine_token_file(cfg)
    orig_entitlements = machine_token_file.entitlements()
    orig_token = machine_token_file.machine_token
    machine_token = orig_token["machineToken"]
    contract_id = orig_token["machineTokenInfo"]["contractInfo"]["id"]

    contract_client = UAContractClient(cfg=cfg)
    resp = contract_client.update_contract_machine(
        machine_token=machine_token, contract_id=contract_id
    )

    machine_token_file.write(resp)
    system.get_machine_id.cache_clear()
    machine_id = resp.get("machineTokenInfo", {}).get(
        "machineId", system.get_machine_id(cfg)
    )
    machine_id_file.write(machine_id)

    process_entitlements_delta(
        cfg,
        orig_entitlements,
        machine_token_file.entitlements(),
        allow_enable=False,
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
        overrides[OVERRIDE_SELECTOR_WEIGHTS["series_overrides"]] = (
            series_overrides
        )

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


def get_enabled_by_default_services(
    cfg: UAConfig, entitlements: Dict[str, Any]
) -> List[EnableByDefaultService]:
    from uaclient.entitlements import entitlement_factory

    enable_by_default_services = []

    for ent_name, ent_value in entitlements.items():
        variant = ent_value.get("obligations", {}).get("use_selector", "")

        try:
            ent = entitlement_factory(cfg=cfg, name=ent_name, variant=variant)
        except exceptions.EntitlementNotFoundError:
            continue

        obligations = ent_value.get("entitlement", {}).get("obligations", {})
        resourceToken = ent_value.get("resourceToken")

        if ent._should_enable_by_default(obligations, resourceToken):
            can_enable, _ = ent.can_enable()
            if can_enable:
                enable_by_default_services.append(
                    EnableByDefaultService(
                        name=ent_name,
                        variant=variant,
                    )
                )

    return enable_by_default_services

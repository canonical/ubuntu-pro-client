import logging
from typing import Any, Dict, List, Optional, Tuple

from uaclient import (
    clouds,
    event_logger,
    exceptions,
    messages,
    serviceclient,
    util,
)
from uaclient.config import UAConfig
from uaclient.defaults import ATTACH_FAIL_DATE_FORMAT
from uaclient.status import UserFacingStatus

API_V1_CONTEXT_MACHINE_TOKEN = "/v1/context/machines/token"
API_V1_TMPL_CONTEXT_MACHINE_TOKEN_RESOURCE = (
    "/v1/contracts/{contract}/context/machines/{machine}"
)
API_V1_RESOURCES = "/v1/resources"
API_V1_TMPL_RESOURCE_MACHINE_ACCESS = (
    "/v1/resources/{resource}/context/machines/{machine}"
)
API_V1_AUTO_ATTACH_CLOUD_TOKEN = "/v1/clouds/{cloud_type}/token"
API_V1_MACHINE_ACTIVITY = "/v1/contracts/{contract}/machine-activity/{machine}"
API_V1_CONTRACT_INFORMATION = "/v1/contract"

event = event_logger.get_event_logger()


class UAContractClient(serviceclient.UAServiceClient):

    cfg_url_base_attr = "contract_url"
    api_error_cls = exceptions.ContractAPIError

    def request_contract_machine_attach(self, contract_token, machine_id=None):
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
        machine_token, _headers = self.request_url(
            API_V1_CONTEXT_MACHINE_TOKEN, data=data, headers=headers
        )
        self.cfg.write_cache("machine-token", machine_token)

        util.get_machine_id.cache_clear()
        machine_id = machine_token.get("machineTokenInfo", {}).get(
            "machineId", data.get("machineId")
        )
        self.cfg.write_cache("machine-id", machine_id)

        return machine_token

    def request_resources(self) -> Dict[str, Any]:
        """Requests list of entitlements available to this machine type."""
        platform = util.get_platform_info()
        query_params = {
            "architecture": platform["arch"],
            "series": platform["series"],
            "kernel": platform["kernel"],
        }
        resource_response, headers = self.request_url(
            API_V1_RESOURCES, query_params=query_params
        )
        return resource_response

    def request_contract_information(
        self, contract_token: str
    ) -> Dict[str, Any]:
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(contract_token)})
        response_data, _response_headers = self.request_url(
            API_V1_CONTRACT_INFORMATION, headers=headers
        )
        return response_data

    def request_auto_attach_contract_token(
        self, *, instance: clouds.AutoAttachCloudInstance
    ):
        """Requests contract token for auto-attach images for Pro clouds.

        @param instance: AutoAttachCloudInstance for the cloud.

        @return: Dict of the JSON response containing the contract-token.
        """
        response, _headers = self.request_url(
            API_V1_AUTO_ATTACH_CLOUD_TOKEN.format(
                cloud_type=instance.cloud_type
            ),
            data=instance.identity_doc,
        )
        self.cfg.write_cache("contract-token", response)
        return response

    def request_resource_machine_access(
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
            machine_id = util.get_machine_id(self.cfg)
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        url = API_V1_TMPL_RESOURCE_MACHINE_ACCESS.format(
            resource=resource, machine=machine_id
        )
        resource_access, headers = self.request_url(url, headers=headers)
        if headers.get("expires"):
            resource_access["expires"] = headers["expires"]
        self.cfg.write_cache(
            "machine-access-{}".format(resource), resource_access
        )
        return resource_access

    def request_machine_token_update(
        self, machine_token: str, contract_id: str, machine_id: str = None
    ) -> Dict:
        """Update existing machine-token for an attached machine."""
        return self._request_machine_token_update(
            machine_token=machine_token,
            contract_id=contract_id,
            machine_id=machine_id,
            detach=False,
        )

    def report_machine_activity(self):
        """Report current activity token and enabled services.

        This will report to the contracts backend all the current
        enabled services in the system.
        """
        contract_id = self.cfg.contract_id
        machine_token = self.cfg.machine_token.get("machineToken")
        machine_id = util.get_machine_id(self.cfg)

        request_data = self._get_activity_info(machine_id)
        url = API_V1_MACHINE_ACTIVITY.format(
            contract=contract_id, machine=machine_id
        )
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})

        response, _ = self.request_url(url, headers=headers, data=request_data)

        # We will update the `machine-token.json` based on the response
        # provided by the server. We expect the response to be
        # a full `activityInfo` object which belongs at the root of
        # `machine-token.json`
        if response:

            machine_token = self.cfg.read_cache("machine-token")
            # The activity information received as a response here
            # will not provide the information inside an activityInfo
            # structure. However, this structure will be reflected when
            # we reach the contract for attach and refresh requests.
            # Because of that, we will store the response directly on
            # the activityInfo key
            machine_token["activityInfo"] = response
            self.cfg.write_cache("machine-token", machine_token)

    def _request_machine_token_update(
        self,
        machine_token: str,
        contract_id: str,
        machine_id: str = None,
        detach: bool = False,
    ) -> Dict:
        """Request machine token refresh from contract server.

        @param machine_token: The machine token needed to talk to
            this contract service endpoint.
        @param contract_id: Unique contract id provided by contract service.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.
        @param detach: Boolean set True if detaching this machine from the
            active contract. Default is False.

        @return: Dict of the JSON response containing refreshed machine-token
        """
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        data = self._get_platform_data(machine_id)
        data["activityInfo"] = self._get_activity_info()
        url = API_V1_TMPL_CONTEXT_MACHINE_TOKEN_RESOURCE.format(
            contract=contract_id, machine=data["machineId"]
        )
        kwargs = {"headers": headers}
        if detach:
            kwargs["method"] = "DELETE"
        else:
            kwargs["method"] = "POST"
            kwargs["data"] = data
        response, headers = self.request_url(url, **kwargs)
        if headers.get("expires"):
            response["expires"] = headers["expires"]
        if not detach:
            self.cfg.write_cache("machine-token", response)
            util.get_machine_id.cache_clear()
            machine_id = response.get("machineTokenInfo", {}).get(
                "machineId", data.get("machineId")
            )
            self.cfg.write_cache("machine-id", machine_id)
        return response

    def _get_platform_data(self, machine_id):
        """Return a dict of platform-related data for contract requests"""
        if not machine_id:
            machine_id = util.get_machine_id(self.cfg)
        platform = util.get_platform_info()
        platform_os = platform.copy()
        arch = platform_os.pop("arch")
        return {
            "machineId": machine_id,
            "architecture": arch,
            "os": platform_os,
        }

    def _get_activity_info(self, machine_id: Optional[str] = None):
        """Return a dict of activity info data for contract requests"""
        from uaclient.entitlements import ENTITLEMENT_CLASSES

        if not machine_id:
            machine_id = util.get_machine_id(self.cfg)

        # If the activityID is null we should provide the endpoint
        # with the instance machine id as the activityID
        activity_id = self.cfg.activity_id or machine_id

        enabled_services = [
            ent(self.cfg).name
            for ent in ENTITLEMENT_CLASSES
            if ent(self.cfg).user_facing_status()[0] == UserFacingStatus.ACTIVE
        ]

        return {
            "activityID": activity_id,
            "activityToken": self.cfg.activity_token,
            "resources": enabled_services,
        }


def process_entitlements_delta(
    past_entitlements: Dict[str, Any],
    new_entitlements: Dict[str, Any],
    allow_enable: bool,
    series_overrides: bool = True,
) -> None:
    """Iterate over all entitlements in new_entitlement and apply any delta
    found according to past_entitlements.

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
    delta_error = False
    unexpected_error = False
    for name, new_entitlement in sorted(new_entitlements.items()):
        try:
            deltas, service_enabled = process_entitlement_delta(
                past_entitlements.get(name, {}),
                new_entitlement,
                allow_enable=allow_enable,
                series_overrides=series_overrides,
            )
        except exceptions.EntitlementNotFoundError:
            continue
        except exceptions.UserFacingError:
            delta_error = True
            event.service_failed(name)
            with util.disable_log_to_console():
                logging.error(
                    "Failed to process contract delta for {name}:"
                    " {delta}".format(name=name, delta=new_entitlement)
                )
        except Exception:
            unexpected_error = True
            event.service_failed(name)
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
    if unexpected_error:
        raise exceptions.UserFacingError(
            msg=messages.UNEXPECTED_ERROR.msg,
            msg_code=messages.UNEXPECTED_ERROR.name,
        )
    elif delta_error:
        raise exceptions.UserFacingError(
            msg=messages.ATTACH_FAILURE_DEFAULT_SERVICES.msg,
            msg_code=messages.ATTACH_FAILURE_DEFAULT_SERVICES.name,
        )


def process_entitlement_delta(
    orig_access: Dict[str, Any],
    new_access: Dict[str, Any],
    allow_enable: bool = False,
    series_overrides: bool = True,
) -> Tuple[Dict, bool]:
    """Process a entitlement access dictionary deltas if they exist.

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
    :return: A tuple containing a dict of processed deltas and a
             boolean indicating if the service was fully processed
    """
    from uaclient.entitlements import entitlement_factory

    if series_overrides:
        util.apply_contract_overrides(new_access)

    deltas = util.get_dict_deltas(orig_access, new_access)
    ret = False
    if deltas:
        name = orig_access.get("entitlement", {}).get("type")
        if not name:
            name = deltas.get("entitlement", {}).get("type")
        if not name:
            msg = messages.INVALID_CONTRACT_DELTAS_SERVICE_TYPE.format(
                orig=orig_access, new=new_access
            )
            raise exceptions.UserFacingError(msg=msg.msg, msg_code=msg.name)
        try:
            ent_cls = entitlement_factory(name)
        except exceptions.EntitlementNotFoundError as exc:
            logging.debug(
                'Skipping entitlement deltas for "%s". No such class', name
            )
            raise exc

        entitlement = ent_cls(assume_yes=allow_enable)
        ret = entitlement.process_contract_deltas(
            orig_access, deltas, allow_enable=allow_enable
        )
    return deltas, ret


def _create_attach_forbidden_message(
    e: exceptions.ContractAPIError
) -> messages.NamedMessage:
    msg = messages.ATTACH_EXPIRED_TOKEN
    if (
        hasattr(e, "api_errors")
        and len(e.api_errors) > 0
        and "info" in e.api_errors[0]
    ):
        info = e.api_errors[0]["info"]
        contract_id = info["contractId"]
        reason = info["reason"]
        reason_msg = None

        if reason == "no-longer-effective":
            date = info["time"].strftime(ATTACH_FAIL_DATE_FORMAT)
            reason_msg = messages.ATTACH_FORBIDDEN_EXPIRED.format(
                contract_id=contract_id, date=date
            )
        elif reason == "not-effective-yet":
            date = info["time"].strftime(ATTACH_FAIL_DATE_FORMAT)
            reason_msg = messages.ATTACH_FORBIDDEN_NOT_YET.format(
                contract_id=contract_id, date=date
            )
        elif reason == "never-effective":
            reason_msg = messages.ATTACH_FORBIDDEN_NEVER.format(
                contract_id=contract_id
            )

        if reason_msg:
            msg = messages.ATTACH_FORBIDDEN.format(reason=reason_msg.msg)
            msg.name = reason_msg.name

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
    :raise UrlError: On failure to contact the server
    """
    orig_token = cfg.machine_token
    orig_entitlements = cfg.entitlements
    if orig_token and contract_token:
        msg = messages.UNEXPECTED_CONTRACT_TOKEN_ON_ATTACHED_MACHINE
        raise exceptions.UserFacingError(msg=msg.msg, msg_code=msg.name)
    contract_client = UAContractClient(cfg)
    if contract_token:  # We are a mid ua-attach and need to get machinetoken
        try:
            contract_client.request_contract_machine_attach(
                contract_token=contract_token
            )
        except exceptions.UrlError as e:
            if isinstance(e, exceptions.ContractAPIError):
                if hasattr(e, "code"):
                    if e.code == 401:
                        raise exceptions.AttachInvalidTokenError()
                    elif e.code == 403:
                        msg = _create_attach_forbidden_message(e)
                        raise exceptions.UserFacingError(
                            msg=msg.msg, msg_code=msg.name
                        )
                raise e
            with util.disable_log_to_console():
                logging.exception(str(e))
            raise exceptions.UserFacingError(
                msg=messages.CONNECTIVITY_ERROR.msg,
                msg_code=messages.CONNECTIVITY_ERROR.name,
            )
    else:
        machine_token = orig_token["machineToken"]
        contract_id = orig_token["machineTokenInfo"]["contractInfo"]["id"]
        contract_client.request_machine_token_update(
            machine_token=machine_token, contract_id=contract_id
        )

    process_entitlements_delta(
        orig_entitlements, cfg.entitlements, allow_enable
    )


def get_available_resources(cfg: UAConfig) -> List[Dict]:
    """Query available resources from the contract server for this machine."""
    client = UAContractClient(cfg)
    resources = client.request_resources()
    return resources.get("resources", [])


def get_contract_information(cfg: UAConfig, token: str) -> Dict[str, Any]:
    """Query contract information for a specific token"""
    client = UAContractClient(cfg)
    return client.request_contract_information(token)

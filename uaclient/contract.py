from datetime import datetime
import logging
import urllib

from uaclient import exceptions
from uaclient import status
from uaclient import serviceclient
from uaclient import util

try:
    from typing import Any, Dict, List, Optional  # noqa: F401
except ImportError:
    # typing isn't available on trusty, so ignore its absence
    pass

API_ERROR_INVALID_TOKEN = "invalid token"
API_ERROR_MISSING_INSTANCE_INFORMATION = "missing instance information"
API_V1_CONTEXT_MACHINE_TOKEN = "/v1/context/machines/token"
API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH = (
    "/v1/contracts/{contract}/context/machines/{machine}"
)
API_V1_RESOURCES = "/v1/resources"
API_V1_TMPL_RESOURCE_MACHINE_ACCESS = (
    "/v1/resources/{resource}/context/machines/{machine}"
)
API_V1_PREMIUM_AWS_TOKEN = "/v1/clouds/aws/token"


class ContractAPIError(util.UrlError):
    def __init__(self, e, error_response):
        super().__init__(e, e.code, e.headers, e.url)
        if "error_list" in error_response:
            self.api_errors = error_response["error_list"]
        else:
            self.api_errors = [error_response]
        for error in self.api_errors:
            error["code"] = error.get("title", error.get("code"))

    def __contains__(self, error_code):
        for error in self.api_errors:
            if error_code == error.get("code"):
                return True
            if error.get("message", "").startswith(error_code):
                return True
        return False

    def __get__(self, error_code, default=None):
        for error in self.api_errors:
            if error["code"] == error_code:
                return error["detail"]
        return default

    def __str__(self):
        prefix = super().__str__()
        details = []
        for err in self.api_errors:
            if not err.get("extra"):
                details.append(err.get("detail", err.get("message", "")))
            else:
                for extra in err["extra"].values():
                    if isinstance(extra, list):
                        details.extend(extra)
                    else:
                        details.append(extra)
        return prefix + ": [" + self.url + "]" + ", ".join(details)


class UAContractClient(serviceclient.UAServiceClient):

    cfg_url_base_attr = "contract_url"
    api_error_cls = ContractAPIError

    def request_contract_machine_attach(self, contract_token, machine_id=None):
        """Requests machine attach to the provided contact_id.

        @param contract_id: Unique contract id provided by contract service.
        @param contract_token: Token string providing authentication to
            ContractBearer service endpoint.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing the machine-token.
        """
        if not machine_id:
            machine_id = util.get_machine_id(self.cfg.data_dir)
        os = util.get_platform_info()
        arch = os.pop("arch")
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(contract_token)})
        data = {"machineId": machine_id, "architecture": arch, "os": os}
        machine_token, _headers = self.request_url(
            API_V1_CONTEXT_MACHINE_TOKEN, data=data, headers=headers
        )
        self.cfg.write_cache("machine-token", machine_token)
        return machine_token

    def request_resources(self) -> "Dict[str, Any]":
        """Requests list of entitlements available to this machine type."""
        platform = util.get_platform_info()
        query_params = {
            "architecture": platform["arch"],
            "series": platform["series"],
            "kernel": platform["kernel"],
        }
        resource_response, headers = self.request_url(
            API_V1_RESOURCES + "?" + urllib.parse.urlencode(query_params)
        )
        return resource_response

    def request_premium_aws_contract_token(self, pkcs7: str):
        """Requests contract token for premium images on AWS.

        @param pkcs7: string obtained from AWS metadata service from
            http://169.254.169.254/latest/dynamic/instance-identity/pkcs7
            from this instance.

        @return: Dict of the JSON response containing the contract-token.
        """
        data = {"pkcs7": pkcs7}
        response, _headers = self.request_url(
            API_V1_PREMIUM_AWS_TOKEN, data=data
        )
        self.cfg.write_cache("contract-token", response)
        return response

    def request_resource_machine_access(
        self,
        machine_token: str,
        resource: str,
        machine_id: "Optional[str]" = None,
    ) -> "Dict[str, Any]":
        """Requests machine access context for a given resource

        @param machine_token: The authentication token needed to talk to
            this contract service endpoint.
        @param resource: Entitlement name.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing entitlement accessInfo.
        """
        if not machine_id:
            machine_id = util.get_machine_id(self.cfg.data_dir)
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

    def request_machine_token_refresh(
        self, machine_token, contract_id, machine_id=None
    ):
        """Request machine token refresh from contract server.

        @param machine_token: The machine token needed to talk to
            this contract service endpoint.
        @param contract_id: Unique contract id provided by contract service.
        @param machine_id: Optional unique system machine id. When absent,
            contents of /etc/machine-id will be used.

        @return: Dict of the JSON response containing refreshed machine-token
        """
        if not machine_id:
            machine_id = util.get_machine_id(self.cfg.data_dir)
        headers = self.headers()
        headers.update({"Authorization": "Bearer {}".format(machine_token)})
        url = API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH.format(
            contract=contract_id, machine=machine_id
        )
        response, headers = self.request_url(url, headers=headers)
        if headers.get("expires"):
            response["expires"] = headers["expires"]
        self.cfg.write_cache("machine-token", response)
        return response


def process_entitlement_delta(orig_access, new_access, allow_enable=False):
    """Process a entitlement access dictionary deltas if they exist.

    :param orig_access: Dict with original entitlement access details before
        contract refresh deltas
    :param orig_access: Dict with updated entitlement access details after
        contract refresh
    :param allow_enable: Boolean set True if allowed to perform the enable
        operation. When False, a message will be logged to inform the user
        about the recommended enabled service.

    :raise UserFacingError: on failure to process deltas.
    :return: Dict of processed deltas
    """
    from uaclient.entitlements import ENTITLEMENT_CLASS_BY_NAME

    util.apply_series_overrides(new_access)
    deltas = util.get_dict_deltas(orig_access, new_access)
    if deltas:
        name = orig_access.get("entitlement", {}).get("type")
        if not name:
            name = deltas.get("entitlement", {}).get("type")
        if not name:
            raise RuntimeError(
                "Could not determine contract delta service type {} {}".format(
                    orig_access, new_access
                )
            )
        try:
            ent_cls = ENTITLEMENT_CLASS_BY_NAME[name]
        except KeyError:
            logging.debug(
                'Skipping entitlement deltas for "%s". No such class', name
            )
            return deltas
        entitlement = ent_cls()
        entitlement.process_contract_deltas(
            orig_access, deltas, allow_enable=allow_enable
        )
    return deltas


def request_updated_contract(
    cfg, contract_token: "Optional[str]" = None, allow_enable=False
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
        raise RuntimeError(
            "Got unexpected contract_token on an already attached machine"
        )
    contract_client = UAContractClient(cfg)
    if contract_token:  # We are a mid ua-attach and need to get machinetoken
        try:
            new_token = contract_client.request_contract_machine_attach(
                contract_token=contract_token
            )
        except util.UrlError as e:
            if isinstance(e, ContractAPIError):
                if API_ERROR_INVALID_TOKEN in e:
                    raise exceptions.UserFacingError(
                        status.MESSAGE_ATTACH_INVALID_TOKEN
                    )
                raise e
            with util.disable_log_to_console():
                logging.exception(str(e))
            raise exceptions.UserFacingError(status.MESSAGE_CONNECTIVITY_ERROR)
    else:
        machine_token = orig_token["machineToken"]
        contract_id = orig_token["machineTokenInfo"]["contractInfo"]["id"]
        new_token = contract_client.request_machine_token_refresh(
            machine_token=machine_token, contract_id=contract_id
        )
    expiry = new_token["machineTokenInfo"]["contractInfo"].get("effectiveTo")
    if expiry:
        if datetime.strptime(expiry, "%Y-%m-%dT%H:%M:%SZ") < datetime.utcnow():
            raise exceptions.UserFacingError(
                status.MESSAGE_CONTRACT_EXPIRED_ERROR
            )
    user_errors = []
    for name, entitlement in sorted(cfg.entitlements.items()):
        if entitlement["entitlement"].get("entitled"):
            # Obtain each entitlement's accessContext for this machine
            new_access = contract_client.request_resource_machine_access(
                new_token["machineToken"], name
            )
        else:
            new_access = entitlement
        try:
            process_entitlement_delta(
                orig_entitlements.get(name, {}),
                new_access,
                allow_enable=allow_enable,
            )
        except exceptions.UserFacingError as e:
            user_errors.append(e)
        except Exception as e:
            with util.disable_log_to_console():
                logging.exception(str(e))
            raise exceptions.UserFacingError(
                "Unexpected error handling Ubuntu Advantage contract changes"
            )
    if user_errors:
        raise exceptions.UserFacingError(
            status.MESSAGE_ATTACH_FAILURE_DEFAULT_SERVICES
        )


def get_available_resources(cfg) -> "List[Dict]":
    """Query available resources from the contrct server for this machine."""
    client = UAContractClient(cfg)
    resources = client.request_resources()
    return resources.get("resources", [])

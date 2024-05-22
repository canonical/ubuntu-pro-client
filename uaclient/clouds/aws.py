import json
import logging
from typing import Any, Dict

from uaclient import exceptions, http, secret_manager, system, util
from uaclient.clouds import AutoAttachCloudInstance

IMDS_IPV4_ADDRESS = "169.254.169.254"
IMDS_IPV6_ADDRESS = "[fd00:ec2::254]"

IMDS_IP_ADDRESS = (IMDS_IPV4_ADDRESS, IMDS_IPV6_ADDRESS)
IMDS_V2_TOKEN_URL = "http://{}/latest/api/token"
IMDS_URL = "http://{}/latest/dynamic/instance-identity/pkcs7"
_IMDS_IID_URL = "http://{}/latest/dynamic/instance-identity/document"

SYS_HYPERVISOR_PRODUCT_UUID = "/sys/hypervisor/uuid"
DMI_PRODUCT_SERIAL = "/sys/class/dmi/id/product_serial"
DMI_PRODUCT_UUID = "/sys/class/dmi/id/product_uuid"

AWS_TOKEN_TTL_SECONDS = "21600"
AWS_TOKEN_PUT_HEADER = "X-aws-ec2-metadata-token"
AWS_TOKEN_REQ_HEADER = AWS_TOKEN_PUT_HEADER + "-ttl-seconds"

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


class UAAutoAttachAWSInstance(AutoAttachCloudInstance):
    _api_token = None
    _ip_address = None

    def _get_imds_url_response(self, url: str, headers):
        response = http.readurl(url, headers=headers, timeout=1)
        if response.code == 200:
            return response.body
        else:
            raise exceptions.CloudMetadataError(
                code=response.code, body=response.body
            )

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(exceptions.CloudMetadataError, retry_sleeps=[0.5, 1, 1])
    def identity_doc(self) -> Dict[str, Any]:
        headers = self._request_imds_v2_token_headers()
        url = IMDS_URL.format(self._ip_address)
        imds_url_response = self._get_imds_url_response(url, headers=headers)
        secret_manager.secrets.add_secret(imds_url_response)
        return {"pkcs7": imds_url_response}

    @util.retry(exceptions.CloudMetadataError, retry_sleeps=[0.5, 1, 1])
    def _get_ii_doc(self) -> Dict:
        """
        Get the instance identity doc associated with the current instance.

        See
        https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/retrieve-iid.html
        for more context.

        @return: Dict containing the instance identity document.
        """
        headers = self._request_imds_v2_token_headers()
        url = _IMDS_IID_URL.format(self._ip_address)
        try:
            ii_doc = json.loads(
                self._get_imds_url_response(url, headers=headers)
            )
        except json.JSONDecodeError as e:
            LOG.debug("Error decoding instance identity document: %s", e)
            return {}
        return ii_doc

    @property  # type: ignore
    def is_likely_pro(self) -> bool:
        """
        Determines if the instance is likely Ubuntu Pro.

        Criteria: if any billing-product or marketplace-product-code is
        present, then is likely a Pro instance.

        @return: Boolean indicating if the instance is likely pro or not.
        """
        ii_doc = self._get_ii_doc()
        billing_products = ii_doc.get("billingProducts", None)
        marketplace_product_codes = ii_doc.get("marketplaceProductCodes", None)
        return bool(billing_products) or bool(marketplace_product_codes)

    def _request_imds_v2_token_headers(self):
        for address in IMDS_IP_ADDRESS:
            try:
                headers = self._get_imds_v2_token_headers(ip_address=address)
            except Exception as e:
                LOG.warning(
                    "Could not reach AWS IMDS at http://%s: %s\n",
                    address,
                    getattr(e, "reason", ""),
                )
            else:
                self._ip_address = address
                break
        if self._ip_address is None:
            raise exceptions.AWSNoValidIMDS(
                addresses=", ".join(IMDS_IP_ADDRESS)
            )
        return headers

    @util.retry(exceptions.CloudMetadataError, retry_sleeps=[1, 2, 5])
    def _get_imds_v2_token_headers(self, ip_address):
        if self._api_token == "IMDSv1":
            return None
        elif self._api_token:
            return {AWS_TOKEN_PUT_HEADER: self._api_token}

        response = http.readurl(
            IMDS_V2_TOKEN_URL.format(ip_address),
            method="PUT",
            headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
            timeout=1,
        )
        if response.code == 200:
            self._api_token = response.body
            secret_manager.secrets.add_secret(self._api_token)
            return {AWS_TOKEN_PUT_HEADER: self._api_token}
        if response.code == 404:
            self._api_token = "IMDSv1"
            return None

        raise exceptions.CloudMetadataError(
            code=response.code, body=response.body
        )

    @property
    def cloud_type(self) -> str:
        return "aws"

    @property
    def is_viable(self) -> bool:
        """This machine is a viable AWSInstance"""
        try:
            hypervisor_uuid = system.load_file(SYS_HYPERVISOR_PRODUCT_UUID)
            if "ec2" == hypervisor_uuid[0:3]:
                return True
        except FileNotFoundError:
            # SYS_HYPERVISOR_PRODUCT_UUID isn't present on all EC2 instance
            # types, fall through
            pass
        # Both DMI product_uuid and product_serial start with 'ec2'
        dmi_uuid = system.load_file(DMI_PRODUCT_UUID).lower()
        dmi_serial = system.load_file(DMI_PRODUCT_SERIAL).lower()
        if "ec2" == dmi_uuid[0:3] == dmi_serial[0:3]:
            return True
        return False

    def should_poll_for_pro_license(self) -> bool:
        """Unsupported"""
        return False

    def is_pro_license_present(self, *, wait_for_change: bool) -> bool:
        raise exceptions.InPlaceUpgradeNotSupportedError()

import logging
from typing import Any, Dict
from urllib.error import HTTPError

from uaclient import exceptions, system, util
from uaclient.clouds import AutoAttachCloudInstance

IMDS_IPV4_ADDRESS = "169.254.169.254"
IMDS_IPV6_ADDRESS = "[fd00:ec2::254]"

IMDS_IP_ADDRESS = (IMDS_IPV4_ADDRESS, IMDS_IPV6_ADDRESS)
IMDS_V2_TOKEN_URL = "http://{}/latest/api/token"
IMDS_URL = "http://{}/latest/dynamic/instance-identity/pkcs7"

SYS_HYPERVISOR_PRODUCT_UUID = "/sys/hypervisor/uuid"
DMI_PRODUCT_SERIAL = "/sys/class/dmi/id/product_serial"
DMI_PRODUCT_UUID = "/sys/class/dmi/id/product_uuid"

AWS_TOKEN_TTL_SECONDS = "21600"
AWS_TOKEN_PUT_HEADER = "X-aws-ec2-metadata-token"
AWS_TOKEN_REQ_HEADER = AWS_TOKEN_PUT_HEADER + "-ttl-seconds"


class UAAutoAttachAWSInstance(AutoAttachCloudInstance):

    _api_token = None
    _ip_address = None

    def _get_imds_url_response(self):
        headers = self._request_imds_v2_token_headers()
        return util.readurl(
            IMDS_URL.format(self._ip_address), headers=headers, timeout=1
        )

    # mypy does not handle @property around inner decorators
    # https://github.com/python/mypy/issues/1362
    @property  # type: ignore
    @util.retry(HTTPError, retry_sleeps=[0.5, 1, 1])
    def identity_doc(self) -> Dict[str, Any]:
        response, _headers = self._get_imds_url_response()
        return {"pkcs7": response}

    def _request_imds_v2_token_headers(self):
        for address in IMDS_IP_ADDRESS:
            try:
                headers = self._get_imds_v2_token_headers(ip_address=address)
            except HTTPError as e:
                raise e
            except Exception as e:
                msg = (
                    "Could not reach AWS IMDS at http://{endpoint}:"
                    " {reason}\n".format(
                        endpoint=address, reason=getattr(e, "reason", "")
                    )
                )
                logging.debug(msg)
            else:
                self._ip_address = address
                break
        if self._ip_address is None:
            raise exceptions.UserFacingError(
                "No valid AWS IMDS endpoint discovered at addresses: %s"
                % ", ".join(IMDS_IP_ADDRESS)
            )
        return headers

    @util.retry(HTTPError, retry_sleeps=[1, 2, 5])
    def _get_imds_v2_token_headers(self, ip_address):
        if self._api_token == "IMDSv1":
            return None
        elif self._api_token:
            return {AWS_TOKEN_PUT_HEADER: self._api_token}
        try:
            response, _headers = util.readurl(
                IMDS_V2_TOKEN_URL.format(ip_address),
                method="PUT",
                headers={AWS_TOKEN_REQ_HEADER: AWS_TOKEN_TTL_SECONDS},
                timeout=1,
            )
        except HTTPError as e:
            if e.code == 404:
                self._api_token = "IMDSv1"
                return None
            else:
                raise

        self._api_token = response
        return {AWS_TOKEN_PUT_HEADER: self._api_token}

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

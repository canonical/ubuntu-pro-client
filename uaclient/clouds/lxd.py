import logging

from uaclient import config, exceptions, http, log, secret_manager, util
from uaclient.clouds import AutoAttachInstance

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))

LXD_INSTANCE_API_SOCKET_PATH = "/dev/lxd/sock"
LXD_INSTANCE_API_ENDPOINT_UBUNTU_PRO = "/1.0/ubuntu-pro"
LXD_INSTANCE_API_ENDPOINT_UBUNTU_PRO_GUEST_TOKEN = "/1.0/ubuntu-pro/token"


class LXDAutoAttachInstance(AutoAttachInstance):
    @property
    def is_viable(self) -> bool:
        return True

    def should_poll_for_pro_license(self) -> bool:
        """Yes, but only once - is_pro_license_present doesn't
        support wait_for_change"""
        return True

    def is_pro_license_present(self, *, wait_for_change: bool) -> bool:
        if wait_for_change:
            # Unsupported
            raise exceptions.CancelProLicensePolling()

        resp = http.unix_socket_request(
            LXD_INSTANCE_API_SOCKET_PATH,
            "GET",
            LXD_INSTANCE_API_ENDPOINT_UBUNTU_PRO,
        )
        if resp.code != 200:
            LOG.warning(
                "LXD instance API returned error for ubuntu-pro query",
                extra=log.extra(code=resp.code, body=resp.body),
            )
            return False
        # returning True will cause auto-attach on launch, so only "on" counts
        return resp.json_dict.get("guest_attach", "off") == "on"

    def acquire_pro_token(self, cfg: config.UAConfig) -> str:
        """
        Cloud-specific implementation of acquiring the pro token using whatever
        method suits the platform
        """
        resp = http.unix_socket_request(
            LXD_INSTANCE_API_SOCKET_PATH,
            "POST",
            LXD_INSTANCE_API_ENDPOINT_UBUNTU_PRO_GUEST_TOKEN,
        )
        if resp.code == 404:
            raise exceptions.LXDAutoAttachNotAvailable()
        elif resp.code == 403:
            raise exceptions.LXDAutoAttachNotAllowed()
        elif resp.code != 200:
            raise exceptions.ExternalAPIError(
                code=resp.code,
                url="unix://{}{}".format(
                    LXD_INSTANCE_API_SOCKET_PATH,
                    LXD_INSTANCE_API_ENDPOINT_UBUNTU_PRO_GUEST_TOKEN,
                ),
                body=resp.body,
            )
        guest_token = resp.json_dict.get("guest_token", "")
        secret_manager.secrets.add_secret(guest_token)
        return guest_token

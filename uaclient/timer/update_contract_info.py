import logging

from uaclient import contract, util
from uaclient.api.u.pro.status.is_attached.v1 import _is_attached
from uaclient.config import UAConfig
from uaclient.files import notices
from uaclient.files.notices import Notice

LOG = logging.getLogger(util.replace_top_level_logger_name(__name__))


def update_contract_info(cfg: UAConfig) -> bool:
    if _is_attached(cfg).is_attached:
        try:
            if contract.is_contract_changed(cfg):
                notices.add(
                    Notice.CONTRACT_REFRESH_WARNING,
                )
            else:
                notices.remove(
                    Notice.CONTRACT_REFRESH_WARNING,
                )
        except Exception as e:
            LOG.warning(
                "Failed to check for change in machine contract. Reason: %s",
                str(e),
                exc_info=e,
            )
            return False
    return True

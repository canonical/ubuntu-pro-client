import logging

from uaclient import contract, messages, util
from uaclient.config import UAConfig
from uaclient.files import notices
from uaclient.files.notices import Notice

LOG = logging.getLogger(__name__)


def update_contract_info(cfg: UAConfig) -> bool:
    if cfg.is_attached:
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
            with util.disable_log_to_console():
                err_msg = messages.UPDATE_CHECK_CONTRACT_FAILURE.format(
                    reason=str(e)
                )
                LOG.warning(err_msg)
            return False
    return True

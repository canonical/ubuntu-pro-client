"""
Update system state module, like status cache or contract cached files
"""

from uaclient.config import UAConfig
from uaclient.status import status


def update_status(cfg: UAConfig) -> bool:
    if cfg.is_attached:
        status(cfg=cfg)
    return True

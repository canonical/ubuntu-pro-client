"""
Update system state module, like status cache or contract cached files
"""

from uaclient.config import UAConfig


def update_status(cfg: UAConfig):
    cfg.status()

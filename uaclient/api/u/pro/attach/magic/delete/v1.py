from uaclient.config import UAConfig
from uaclient.contract import UAContractClient


def delete(magic_token: str, cfg: UAConfig = None) -> None:
    if cfg is None:
        cfg = UAConfig()

    contract = UAContractClient(cfg)
    contract.revoke_magic_attach_token(magic_token)

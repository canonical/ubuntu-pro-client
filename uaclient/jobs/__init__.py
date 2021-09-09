from uaclient import config, util
from uaclient.clouds.identity import get_cloud_type


def enable_license_check_if_applicable(cfg: config.UAConfig):
    series = util.get_platform_info()["series"]
    if "gce" in get_cloud_type() and util.is_lts(series):
        cfg.write_cache("marker-license-check", "")


def disable_license_check_if_applicable(cfg: config.UAConfig):
    if cfg.cache_key_exists("marker-license-check"):
        cfg.delete_cache_key("marker-license-check")
        util.subp(["systemctl", "stop", "ua-license-check.timer"])

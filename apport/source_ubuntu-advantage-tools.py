import os
import tempfile

from apport.hookutils import attach_file_if_exists
from uaclient import defaults
from uaclient.actions import collect_logs
from uaclient.config import UAConfig


def add_info(report, ui=None):
    report["LaunchpadPrivate"] = "1"
    report["LaunchpadSubscribe"] = "ua-client"
    cfg = UAConfig()
    with tempfile.TemporaryDirectory() as output_dir:
        collect_logs(cfg, output_dir)
        auto_include_log_files = {
            "cloud-id.txt",
            "cloud-id.txt-error",
            "ua-status.json",
            "ua-status.json-error",
            "livepatch-status.txt",
            "livepatch-status.txt-error",
            "pro-journal.txt",
            os.path.basename(cfg.cfg_path),
            os.path.basename(cfg.log_file),
            os.path.basename(cfg.data_path("jobs-status")),
            os.path.basename(defaults.CONFIG_DEFAULTS["log_file"]),
        }
        for f in auto_include_log_files:
            attach_file_if_exists(report, os.path.join(output_dir, f), key=f)

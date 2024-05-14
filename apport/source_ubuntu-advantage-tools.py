import os
import tempfile

from apport.hookutils import attach_file_if_exists
from uaclient import defaults
from uaclient.actions import APPARMOR_PROFILES, collect_logs
from uaclient.config import UAConfig
from uaclient.files.state_files import timer_jobs_state_file


def add_info(report, ui=None):
    report["LaunchpadPrivate"] = "1"
    report["LaunchpadSubscribe"] = "ua-client"
    cfg = UAConfig()
    apparmor_files = [os.path.basename(f) for f in APPARMOR_PROFILES]
    with tempfile.TemporaryDirectory() as output_dir:
        collect_logs(cfg, output_dir)
        auto_include_log_files = {
            "cloud-id.txt",
            "cloud-id.txt-error",
            "pro-status.json",
            "pro-status.json-error",
            "livepatch-status.txt",
            "livepatch-status.txt-error",
            "pro-journal.txt",
            "apparmor_logs.txt",
            *apparmor_files,
            os.path.basename(cfg.cfg_path),
            os.path.basename(cfg.log_file),
            os.path.basename(timer_jobs_state_file.path),
            os.path.basename(defaults.CONFIG_DEFAULTS["log_file"]),
        }
        for f in auto_include_log_files:
            attach_file_if_exists(report, os.path.join(output_dir, f), key=f)

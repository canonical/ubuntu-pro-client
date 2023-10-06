#!/usr/bin/env python3

"""
Patch status.json file to avoid tracebacks for non-root from `ua status`

Between 27.1 and 27.2 status.json broke schema key backward-compatibility.

Running `ua status` as non-root users does not generate a new status.json with
the updated status.json schema so the logic which renders ua status
information will traceback on KeyErrors.

Since we haven't introduced official schema versioning in Pro client yet,
this patch is a stop-gap until official schema version handling is
delivered.
"""

import copy
import json
import logging

from uaclient import config, defaults, log, system, util

LOG = logging.getLogger("ubuntupro.lib.patch_status_json")


def patch_status_json_schema_0_1(status_file: str):
    """Patch incompatible status.json file schema to align with version 0.1."""
    content = system.load_file(status_file)
    try:
        status = json.loads(content, cls=util.DatetimeAwareJSONDecoder)
    except ValueError as e:
        LOG.warning(
            "Unable to patch /var/lib/ubuntu-advantage/status.json: %s", str(e)
        )
        return
    new_status = copy.deepcopy(status)
    if float(status.get("_schema_version", 0)) >= 0.1:
        return  # Already have version 0.1 from daily PPA
    LOG.debug("Patching /var/lib/ubuntu-advantage/status.json schema")
    new_status["_schema_version"] = "0.1"
    new_status["account"] = {
        "name": new_status.pop("account", ""),
        "id": new_status.pop("account-id", ""),
    }
    new_status["contract"] = {
        "tech_support_level": new_status.pop("techSupportLevel", "n/a"),
        "name": new_status.pop("subscription", ""),
        "id": new_status.pop("subscription-id", ""),
    }
    if "configStatus" in new_status:
        new_status["execution_status"] = new_status.pop("configStatus")
    if "configStatusDetails" in new_status:
        new_status["execution_details"] = new_status.pop("configStatusDetails")
    try:
        status_content = json.dumps(
            new_status, cls=util.DatetimeAwareJSONEncoder
        )
    except ValueError as e:
        LOG.warning(
            "Unable to patch /var/lib/ubuntu-advantage/status.json: %s", str(e)
        )
    system.write_file(status_file, status_content)


if __name__ == "__main__":
    log.setup_cli_logging(logging.DEBUG, defaults.CONFIG_DEFAULTS["log_level"])
    cfg = config.UAConfig()
    log.setup_cli_logging(cfg.log_level, cfg.log_file)
    patch_status_json_schema_0_1(
        status_file="/var/lib/ubuntu-advantage/status.json"
    )

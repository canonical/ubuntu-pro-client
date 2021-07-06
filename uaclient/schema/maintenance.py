"""General maintenance functions to manipulate schema versions."""

from typing import Dict

import copy
import glob
import importlib
import logging
import os
import re

from uaclient.config import UAConfig


def get_patches_by_version(glob_path_str: str) -> Dict[float, str]:
    """Return a dict of patch files from dir_name keyed by patch version."""
    patches_dict = {}
    for patch_path in glob.glob(glob_path_str):
        match = re.match(r".*\/status_(?P<ver>[.\d]+)\.py", patch_path)
        if not match:
            logging.warning("Ignoring schema patch file {}".format(patch_path))
            continue
        patch_file = os.path.basename(patch_path)
        patches_dict[float(match.groupdict()["ver"])] = patch_file.replace(
            ".py", ""
        )
    return patches_dict


def get_compat_schema(cfg: UAConfig, status_dict: Dict):
    """Read status json from status_file, apply all patches and write it."""
    status = copy.deepcopy(status_dict)
    patches = get_patches_by_version(
        "{}/status*py".format(os.path.dirname(__file__))
    )
    # schemas key will contain backward compat schema versions for old clients
    schemas = status.pop("schemas", {})
    if "_schema_version" in status:
        current_ver = float(status["_schema_version"])
    else:
        current_ver = 0.1
    # Preserve current version in under "schemas" key
    schemas[current_ver] = copy.deepcopy(status)

    downgrade_callables = {}
    # Apply patches and preserve each new schema version
    for patch_ver in sorted(patches):
        mod = importlib.import_module(
            "uaclient.schema.{}".format(patches[patch_ver])
        )
        if patch_ver > current_ver:
            # preserve current_ver and apply patches
            upgrade = getattr(mod, "up")
            schemas[patch_ver] = upgrade(cfg, schemas[current_ver])
            current_ver = patch_ver
        else:
            downgrade_callables[patch_ver] = getattr(mod, "down")
    # Preserve backwards-compatible earlier versions of status in "schemas"
    for downgrade_ver in sorted(downgrade_callables, reverse=True):
        import pdb

        pdb.set_trace()
        downgrade = downgrade_callables[downgrade_ver]
        downgrade_status = downgrade(cfg, schemas[downgrade_ver])
        schemas[downgrade_status["_schema_version"]] = downgrade_status

    status["schemas"] = schemas
    return status

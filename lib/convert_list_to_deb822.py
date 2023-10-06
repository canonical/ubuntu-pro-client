#!/usr/bin/env python3

"""
This script is called after running do-release-upgrade in a machine.
This converts list files to deb822 files when upgrading to Noble.
"""

import logging
import os
import sys

from aptsources.sourceslist import SourceEntry  # type: ignore

from uaclient import defaults, entitlements
from uaclient.apt import _get_sources_file_content
from uaclient.config import UAConfig
from uaclient.log import setup_cli_logging
from uaclient.system import (
    ensure_file_absent,
    get_release_info,
    load_file,
    write_file,
)
from uaclient.util import set_filename_extension

if __name__ == "__main__":
    series = get_release_info().series
    if series != "noble":
        sys.exit(0)

    setup_cli_logging(logging.DEBUG, defaults.CONFIG_DEFAULTS["log_file"])
    cfg = UAConfig()

    for entitlement_class in entitlements.ENTITLEMENT_CLASSES:
        if not issubclass(
            entitlement_class, entitlements.repo.RepoEntitlement
        ):
            continue

        entitlement = entitlement_class(cfg)

        filename = set_filename_extension(entitlement.repo_file, "list")
        if os.path.exists(filename):
            # If do-release-upgrade commented out the file, whether the
            # repository is not reachable or is considered a third party, then
            # it will be handled in upgrade_lts_contract. This script only
            # changes services which are enabled, active and reachable.
            valid_sources = [
                SourceEntry(line)
                for line in load_file(filename).strip().split("\n")
                if line.strip().startswith("deb")
            ]
            if valid_sources:
                # get this information from the file, to avoid interacting with
                # the entitlement_config
                suites = list(set(source.dist for source in valid_sources))
                repo_url = valid_sources[0].uri
                include_deb_src = any(
                    source.type == "deb-src" for source in valid_sources
                )
                content = _get_sources_file_content(
                    suites,
                    series,
                    True,
                    repo_url,
                    entitlement.repo_key_file,
                    include_deb_src,
                )
                write_file(entitlement.repo_file, content)

            ensure_file_absent(filename)

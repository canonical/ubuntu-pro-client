import logging
import os

from uaclient import exceptions
from uaclient import util


def export_gpg_key_from_keyring(
    key_id: str, source_keyring_file: str, destination_keyfile: str
) -> None:
    """Export a specific key from source_keyring_file into destination_keyfile

    :param key_id: Long fingerprint of key to export.
    :param source_keyring_file: The keyring file from which to export.
    :param destination_keyfile: The filename created with the single exported
        key.

    :raise UserFacingError: Any GPG errors or if specific key does not exist in
        the source_keyring_file.
    """
    export_cmd = [
        "gpg",
        "--output",
        destination_keyfile,
        "--yes",
        "--no-auto-check-trustdb",
        "--no-options",
        "--no-default-keyring",
        "--keyring",
        source_keyring_file,
        "--export",
        key_id,
    ]
    logging.debug("Exporting GPG key %s from %s", key_id, source_keyring_file)
    try:
        out, err = util.subp(export_cmd)
    except util.ProcessExecutionError as exc:
        with util.disable_log_to_console():
            logging.error(str(exc))
        raise exceptions.UserFacingError(
            "Unable to export GPG keys from keyring {}".format(
                source_keyring_file
            )
        )
    if "nothing exported" in err:
        raise exceptions.UserFacingError(
            "GPG key '{}' not found in {}".format(key_id, source_keyring_file)
        )
    if not os.path.exists(destination_keyfile):
        msg = "Unexpected error exporting GPG key '{}' from {}".format(
            key_id, source_keyring_file
        )
        with util.disable_log_to_console():
            logging.error(msg + " Error: {}".format(err))
        raise exceptions.UserFacingError(msg)

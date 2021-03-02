import logging
import os
import shutil

from uaclient import exceptions


def export_gpg_key(source_keyfile: str, destination_keyfile: str) -> None:
    """Copy a specific key from source_keyring_dir into destination_keyfile

    :param source_keyfile: Path of source keyring file to export.
    :param destination_keyfile: The filename created with the single exported
        key.

    :raise UserFacingError: Any GPG errors or if specific key does not exist in
        the source_keyring_file.
    """
    logging.debug("Exporting GPG key %s", source_keyfile)
    if not os.path.exists(source_keyfile):
        raise exceptions.UserFacingError(
            "GPG key '{}' not found.".format(source_keyfile)
        )
    shutil.copy(source_keyfile, destination_keyfile)
    os.chmod(destination_keyfile, 0o644)

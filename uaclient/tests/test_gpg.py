import os
import pytest

from uaclient import exceptions, gpg, util
from uaclient.testing import data


@pytest.yield_fixture
def home_dir(tmpdir):
    home = tmpdir.join("home")
    home.mkdir()

    unset = object()
    old_home = os.environ.get("HOME", unset)

    os.environ["HOME"] = home.strpath
    yield

    if old_home is unset:
        del os.environ["HOME"]
    else:
        os.environ["HOME"] = old_home


class TestExportGPGKey:
    def test_key_error_on_missing_keyfile(self, home_dir, tmpdir):
        """Raise UserFacingError when source_keyfile is not found."""
        src_keyfile = tmpdir.join("nothere").strpath
        destination_keyfile = tmpdir.join("destination_keyfile").strpath
        # known valid gpg key which will not exist in source_keyring_dir
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            gpg.export_gpg_key(
                source_keyfile=src_keyfile,
                destination_keyfile=destination_keyfile,
            )

        error_msg = "GPG key '{}' not found".format(src_keyfile)
        assert error_msg in str(excinfo.value)
        assert not os.path.exists(destination_keyfile)

    def test_export_single_key_from_keyring_dir(self, home_dir, tmpdir):
        """Only a single key is exported from a multi-key source keyring."""
        source_key1 = tmpdir.join(
            "ubuntu-advantage-esm-{}.gpg".format(data.GPG_KEY1_ID)
        )
        source_key2 = tmpdir.join(
            "ubuntu-advantage-cc-eal-{}.gpg".format(data.GPG_KEY2_ID)
        )
        destination_keyfile = tmpdir.join("destination_key").strpath
        # Create keyring with both ESM and CC-EAL2 keys
        source_key1.write(data.GPG_KEY1, "wb")
        source_key2.write(data.GPG_KEY2, "wb")
        gpg.export_gpg_key(
            source_keyfile=source_key1.strpath,
            destination_keyfile=destination_keyfile,
        )
        gpg_dest_list_keys = [
            "gpg",
            "--no-auto-check-trustdb",
            "--options",
            "/dev/null",
            "--no-default-keyring",
            "--keyring",
            destination_keyfile,
            "--list-keys",
        ]
        dest_out, _err = util.subp(gpg_dest_list_keys)

        assert "Ubuntu Common Criteria EAL2" in dest_out
        # ESM didn't get exported
        assert "Extended Security Maintenance" not in dest_out

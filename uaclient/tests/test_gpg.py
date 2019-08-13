import os
import pytest

from uaclient import exceptions, gpg, util
from uaclient.testing import data


@pytest.yield_fixture
def home_dir(tmpdir):
    home = tmpdir.join('home')
    home.mkdir()

    unset = object()
    old_home = os.environ.get('HOME', unset)

    os.environ['HOME'] = home.strpath
    yield

    if old_home is unset:
        del os.environ['HOME']
    else:
        os.environ['HOME'] = old_home


class TestExportGPGKeyFromKeyring:
    def test_key_error_on_missing_key(self, home_dir, tmpdir):
        """Raise UserFacingError when key_id is not in source_keyring_file."""
        src_keyring = tmpdir.join('ubuntu-advantage-keyring')
        src_keyring.write('')
        destination_keyfile = tmpdir.join('destination_keyfile').strpath
        # known valid gpg key which will not exist in src_keyring
        key_id = '7CF05F218D72BB5B945693CA6FE15DD1E3510761'
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            gpg.export_gpg_key_from_keyring(
                key_id=key_id,
                source_keyring_file=src_keyring.strpath,
                destination_keyfile=destination_keyfile,
            )

        error_msg = "GPG key '%s' not found in %s" % (
            key_id,
            src_keyring.strpath,
        )
        assert error_msg in str(excinfo.value)
        assert not os.path.exists(destination_keyfile)

    def test_user_facing_error_on_invalid_keyring_packet(
        self, caplog_text, home_dir, tmpdir
    ):
        """Raise UserFacingError on invalid keyring packet. Log cmd error."""
        source_keyring = tmpdir.join('keyring').strpath
        destination_keyfile = tmpdir.join('destination_key').strpath
        key_id = '3CB3DF682220A643B43065E9B30EDAA63D8F61D0'
        # Create bogus keyring with invalid packet which causes gpg errors
        tmpdir.join('keyring').write(b'\n', mode='wb')
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            gpg.export_gpg_key_from_keyring(
                key_id=key_id,
                source_keyring_file=source_keyring,
                destination_keyfile=destination_keyfile,
            )
        msg = "Failed running command 'gpg --output {}".format(
            destination_keyfile
        )
        assert 'ERROR    {}'.format(msg) in caplog_text()
        assert not os.path.exists(destination_keyfile)
        msg = 'Unable to export GPG keys from keyring %s' % (source_keyring,)
        assert msg == str(excinfo.value)

    def test_export_single_key_from_keyring(self, home_dir, tmpdir):
        """Only a single key is exported from a multi-key source keyring."""
        source_keyring = tmpdir.join('keyring').strpath
        destination_keyfile = tmpdir.join('destination_key').strpath
        # Create keyring with both ESM and CC-EAL2 keys
        with open(source_keyring, 'wb') as stream:
            stream.write(data.GPG_KEY1 + data.GPG_KEY2)
        gpg.export_gpg_key_from_keyring(
            key_id=data.GPG_KEY1_ID,
            source_keyring_file=source_keyring,
            destination_keyfile=destination_keyfile,
        )
        gpg_src_list_keys = [
            'gpg',
            '--no-auto-check-trustdb',
            '--options',
            '/dev/null',
            '--no-default-keyring',
            '--keyring',
            source_keyring,
            '--list-keys',
        ]
        src_out, _err = util.subp(gpg_src_list_keys)
        # List all keys in the distrination_keyfile
        gpg_dest_list_keys = [
            'gpg',
            '--no-auto-check-trustdb',
            '--options',
            '/dev/null',
            '--no-default-keyring',
            '--keyring',
            destination_keyfile,
            '--list-keys',
        ]
        dest_out, _err = util.subp(gpg_dest_list_keys)
        assert 'Ubuntu Common Criteria EAL2' in src_out
        assert 'Extended Security Maintenance' in src_out

        assert 'Ubuntu Common Criteria EAL2' in dest_out
        # ESM didn't get exported
        assert 'Extended Security Maintenance' not in dest_out

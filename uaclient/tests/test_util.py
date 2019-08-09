"""Tests related to uaclient.util module."""
import datetime
import json
import logging
import posix
import subprocess
import uuid

import mock
import pytest

from uaclient import cli, util

PRIVACY_POLICY_URL = (
    "https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
)

OS_RELEASE_DISCO = """\
NAME="Ubuntu"
VERSION="19.04 (Disco Dingo)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu Disco Dingo (development branch)"
VERSION_ID="19.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="{}"
VERSION_CODENAME=disco
UBUNTU_CODENAME=disco
""".format(
    PRIVACY_POLICY_URL
)

OS_RELEASE_BIONIC = """\
NAME="Ubuntu"
VERSION="18.04.1 LTS (Bionic Beaver)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 18.04.1 LTS"
VERSION_ID="18.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="{}"
VERSION_CODENAME=bionic
UBUNTU_CODENAME=bionic
""".format(
    PRIVACY_POLICY_URL
)

OS_RELEASE_XENIAL = """\
NAME="Ubuntu"
VERSION="16.04.5 LTS (Xenial Xerus)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 16.04.5 LTS"
VERSION_ID="16.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
VERSION_CODENAME=xenial
UBUNTU_CODENAME=xenial
"""

OS_RELEASE_TRUSTY = """\
NAME="Ubuntu"
VERSION="14.04.5 LTS, Trusty Tahr"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 14.04.5 LTS"
VERSION_ID="14.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
"""


class TestGetDictDeltas:
    @pytest.mark.parametrize(
        'value1,value2', (('val1', 'val2'), ([1], [2]), ((1, 2), (3, 4)))
    )
    def test_non_dict_diffs_return_new_value(self, value1, value2):
        """When two values differ and are not a dict return the new value."""
        expected = {'key': value2}
        assert expected == util.get_dict_deltas(
            {'key': value1}, {'key': value2}
        )

    def test_diffs_return_new_keys_and_values(self):
        """New keys previously absent will be returned in the delta."""
        expected = {'newkey': 'val'}
        assert expected == util.get_dict_deltas(
            {'k': 'v'}, {'newkey': 'val', 'k': 'v'}
        )

    def test_diffs_return_dropped_keys_set_dropped(self):
        """Old keys which are now dropped are returned as DROPPED_KEY."""
        expected = {'oldkey': util.DROPPED_KEY, 'oldkey2': util.DROPPED_KEY}
        assert expected == util.get_dict_deltas(
            {'oldkey': 'v', 'k': 'v', 'oldkey2': {}}, {'k': 'v'}
        )

    def test_return_only_keys_which_represent_deltas(self):
        """Only return specific keys which have deltas."""
        orig_dict = {
            '1': '1',
            '2': 'orig2',
            '3': {'3.1': '3.1', '3.2': 'orig3.2'},
            '4': {'4.1': '4.1'},
        }
        new_dict = {
            '1': '1',
            '2': 'new2',
            '3': {'3.1': '3.1', '3.2': 'new3.2'},
            '4': {'4.1': '4.1'},
        }
        expected = {'2': 'new2', '3': {'3.2': 'new3.2'}}
        assert expected == util.get_dict_deltas(orig_dict, new_dict)


class TestIsContainer:
    @mock.patch('uaclient.util.subp')
    def test_true_systemd_detect_virt_success(self, m_subp):
        """Return True when systemd-detect virt exits success."""
        m_subp.return_value = '', ''
        assert True is util.is_container()
        calls = [mock.call(['systemd-detect-virt', '--quiet', '--container'])]
        assert calls == m_subp.call_args_list

    @mock.patch('uaclient.util.subp')
    def test_true_on_run_container_type(self, m_subp, tmpdir):
        """Return True when /run/container_type exists."""
        m_subp.side_effect = OSError('No systemd-detect-virt utility')
        tmpdir.join('container_type').write('')

        assert True is util.is_container(run_path=tmpdir.strpath)
        calls = [mock.call(['systemd-detect-virt', '--quiet', '--container'])]
        assert calls == m_subp.call_args_list

    @mock.patch('uaclient.util.subp')
    def test_true_on_run_systemd_container(self, m_subp, tmpdir):
        """Return True when /run/systemd/container exists."""
        m_subp.side_effect = OSError('No systemd-detect-virt utility')
        tmpdir.join('systemd/container').write('', ensure=True)

        assert True is util.is_container(run_path=tmpdir.strpath)
        calls = [mock.call(['systemd-detect-virt', '--quiet', '--container'])]
        assert calls == m_subp.call_args_list

    @mock.patch('uaclient.util.subp')
    def test_false_on_non_sytemd_detect_virt_and_no_runfiles(
        self, m_subp, tmpdir
    ):
        """Return False when sytemd-detect-virt erros and no /run/* files."""
        m_subp.side_effect = OSError('No systemd-detect-virt utility')

        with mock.patch('uaclient.util.os.path.exists') as m_exists:
            m_exists.return_value = False
            assert False is util.is_container(run_path=tmpdir.strpath)
        calls = [mock.call(['systemd-detect-virt', '--quiet', '--container'])]
        assert calls == m_subp.call_args_list
        exists_calls = [
            mock.call(tmpdir.join('container_type').strpath),
            mock.call(tmpdir.join('systemd/container').strpath),
        ]
        assert exists_calls == m_exists.call_args_list


class TestSubp:
    def test_raise_error_on_timeout(self):
        """When cmd exceeds the timeout raises a TimeoutExpired error."""
        with pytest.raises(subprocess.TimeoutExpired) as excinfo:
            util.subp(['sleep', '2'], timeout=0)
        msg = "Command '[b'sleep', b'2']' timed out after 0 seconds"
        assert msg == str(excinfo.value)

    @mock.patch('uaclient.util.time.sleep')
    def test_default_do_not_retry_on_failure_return_code(self, m_sleep):
        """When no retry_sleeps are specified, do not retry failures."""
        with pytest.raises(util.ProcessExecutionError) as excinfo:
            util.subp(['ls', '--bogus'])

        expected_error = (
            "Failed running command 'ls --bogus' [exit(2)]."
            " Message: ls: unrecognized option"
        )
        assert expected_error in str(excinfo.value)
        assert 0 == m_sleep.call_count  # no retries

    @mock.patch('uaclient.util.time.sleep')
    def test_no_error_on_accepted_return_codes(self, m_sleep):
        """When rcs list includes the exit code, do not raise an error."""
        out, err = util.subp(['ls', '--bogus'], rcs=[2])

        assert '' == out
        assert 'ls: unrecognized option \'--bogus\'' in err
        assert 0 == m_sleep.call_count  # no retries

    @mock.patch('uaclient.util.time.sleep')
    def test_retry_with_specified_sleeps_on_error(self, m_sleep):
        """When retry_sleeps given, use defined sleeps between each retry."""
        with pytest.raises(util.ProcessExecutionError) as excinfo:
            util.subp(['ls', '--bogus'], retry_sleeps=[1, 3, 0.4])

        expected_error = 'Failed running command \'ls --bogus\' [exit(2)]'
        assert expected_error in str(excinfo.value)
        expected_sleeps = [mock.call(1), mock.call(3), mock.call(0.4)]
        assert expected_sleeps == m_sleep.call_args_list

    @mock.patch('uaclient.util.time.sleep')
    def test_retry_doesnt_consume_retry_sleeps(self, m_sleep):
        """When retry_sleeps given, use defined sleeps between each retry."""
        sleeps = [1, 3, 0.4]
        expected_sleeps = sleeps.copy()
        with pytest.raises(util.ProcessExecutionError):
            util.subp(['ls', '--bogus'], retry_sleeps=sleeps)

        assert expected_sleeps == sleeps


class TestParseOSRelease:
    def test_parse_os_release(self, tmpdir):
        """parse_os_release returns a dict of values from /etc/os-release."""
        release_file = tmpdir.join('os-release')
        release_file.write(OS_RELEASE_TRUSTY)
        expected = {
            'BUG_REPORT_URL': 'http://bugs.launchpad.net/ubuntu/',
            'HOME_URL': 'http://www.ubuntu.com/',
            'ID': 'ubuntu',
            'ID_LIKE': 'debian',
            'NAME': 'Ubuntu',
            'PRETTY_NAME': 'Ubuntu 14.04.5 LTS',
            'SUPPORT_URL': 'http://help.ubuntu.com/',
            'VERSION': '14.04.5 LTS, Trusty Tahr',
            'VERSION_ID': '14.04',
        }
        assert expected == util.parse_os_release(release_file.strpath)


class TestGetPlatformInfo:
    @mock.patch('uaclient.util.subp')
    @mock.patch('uaclient.util.parse_os_release')
    def test_get_platform_info_error_no_version(self, m_parse, m_subp):
        """get_platform_info errors when it cannot parse os-release."""
        m_parse.return_value = {'VERSION': 'junk'}
        with pytest.raises(RuntimeError) as excinfo:
            util.get_platform_info()
        expected_msg = (
            'Could not parse /etc/os-release VERSION: junk (modified to junk)'
        )
        assert expected_msg == str(excinfo.value)

    @pytest.mark.parametrize(
        'series,release,version,os_release_content',
        [
            ('trusty', '14.04', '14.04 LTS (Trusty Tahr)', OS_RELEASE_TRUSTY),
            ('xenial', '16.04', '16.04 LTS (Xenial Xerus)', OS_RELEASE_XENIAL),
            (
                'bionic',
                '18.04',
                '18.04 LTS (Bionic Beaver)',
                OS_RELEASE_BIONIC,
            ),
            ('disco', '19.04', '19.04 (Disco Dingo)', OS_RELEASE_DISCO),
        ],
    )
    def test_get_platform_info_with_version(
        self, series, release, version, os_release_content, tmpdir
    ):
        release_file = tmpdir.join('os-release')
        release_file.write(os_release_content)
        parse_dict = util.parse_os_release(release_file.strpath)

        expected = {
            'arch': 'arm64',
            'distribution': 'Ubuntu',
            'kernel': 'kernel-ver',
            'release': release,
            'series': series,
            'type': 'Linux',
            'version': version,
        }

        with mock.patch('uaclient.util.parse_os_release') as m_parse:
            with mock.patch('uaclient.util.os.uname') as m_uname:
                m_parse.return_value = parse_dict
                # (sysname, nodename, release, version, machine)
                m_uname.return_value = posix.uname_result(
                    ('', '', 'kernel-ver', '', 'arm64')
                )
                assert expected == util.get_platform_info()


class TestApplySeriesOverrides:
    def test_error_on_non_entitlement_dict(self):
        """Raise a runtime error when seeing invalid dict type."""
        with pytest.raises(RuntimeError) as exc:
            util.apply_series_overrides({'some': 'dict'})
        error = (
            'Expected entitlement access dict. Missing "entitlement" key:'
            " {'some': 'dict'}"
        )
        assert error == str(exc.value)

    @mock.patch(
        'uaclient.util.get_platform_info', return_value={'series': 'xenial'}
    )
    def test_mutates_orig_access_dict(self, _):
        """Mutate orig_access dict when called."""
        orig_access = {
            'entitlement': {
                'a': {'a1': 'av1', 'a2': {'aa2': 'aav2'}},
                'b': 'b1',
                'c': 'c1',
                'series': {
                    'trusty': {'a': 't1'},
                    'xenial': {'a': {'a2': {'aa2': 'xxv2'}}, 'b': 'bx1'},
                },
            }
        }
        expected = {
            'entitlement': {
                'a': {'a1': 'av1', 'a2': {'aa2': 'xxv2'}},
                'b': 'bx1',
                'c': 'c1',
            }
        }
        util.apply_series_overrides(orig_access)
        assert orig_access == expected

    @mock.patch(
        'uaclient.util.get_platform_info', return_value={'series': 'xenial'}
    )
    def test_missing_keys_are_handled(self, _):
        orig_access = {
            'entitlement': {
                'series': {'xenial': {'directives': {'suites': ['xenial']}}}
            }
        }
        expected = {'entitlement': {'directives': {'suites': ['xenial']}}}

        util.apply_series_overrides(orig_access)

        assert expected == orig_access


class TestGetMachineId:
    def test_get_machine_id_from_etc_machine_id(self, tmpdir):
        """Presence of /etc/machine-id is returned if it exists."""
        etc_machine_id = tmpdir.join('etc-machine-id')
        assert '/etc/machine-id' == util.ETC_MACHINE_ID
        etc_machine_id.write('etc-machine-id')
        with mock.patch(
            'uaclient.util.ETC_MACHINE_ID', etc_machine_id.strpath
        ):
            value = util.get_machine_id(data_dir=None)
        assert 'etc-machine-id' == value

    def test_get_machine_id_from_var_lib_dbus_machine_id(self, tmpdir):
        """On trusty, machine id lives in of /var/lib/dbus/machine-id."""
        etc_machine_id = tmpdir.join('etc-machine-id')
        dbus_machine_id = tmpdir.join('dbus-machine-id')
        assert '/var/lib/dbus/machine-id' == util.DBUS_MACHINE_ID
        dbus_machine_id.write('dbus-machine-id')
        with mock.patch(
            'uaclient.util.DBUS_MACHINE_ID', dbus_machine_id.strpath
        ):
            with mock.patch(
                'uaclient.util.ETC_MACHINE_ID', etc_machine_id.strpath
            ):
                value = util.get_machine_id(data_dir=None)
        assert 'dbus-machine-id' == value

    def test_get_machine_id_uses_machine_id_from_data_dir(self, tmpdir):
        """When no machine-id is found, use machine-id from data_dir."""

        data_machine_id = tmpdir.join('machine-id')
        data_machine_id.write('data-machine-id')

        def fake_exists(path):
            return bool(path == data_machine_id.strpath)

        with mock.patch('uaclient.util.os.path.exists') as m_exists:
            m_exists.side_effect = fake_exists
            value = util.get_machine_id(data_dir=tmpdir.strpath)
        assert 'data-machine-id' == value

    def test_get_machine_id_create_machine_id_in_data_dir(self, tmpdir):
        """When no machine-id is found, create one in data_dir using uuid4."""
        data_machine_id = tmpdir.join('machine-id')

        with mock.patch('uaclient.util.os.path.exists') as m_exists:
            with mock.patch('uaclient.util.uuid.uuid4') as m_uuid4:
                m_exists.return_value = False
                m_uuid4.return_value = uuid.UUID(
                    '0123456789abcdef0123456789abcdef'
                )
                value = util.get_machine_id(data_dir=tmpdir.strpath)
        assert '01234567-89ab-cdef-0123-456789abcdef' == value
        assert '01234567-89ab-cdef-0123-456789abcdef' == data_machine_id.read()


class TestIsServiceUrl:
    @pytest.mark.parametrize(
        'url,is_valid',
        (('http://asdf', True), ('http://asdf/', True), ('asdf', False)),
    )
    def test_is_valid_url(self, url, is_valid):
        ret = util.is_service_url(url)
        assert is_valid is ret


class TestReadurl:
    def test_simple_call_with_url_works(self):
        with mock.patch('uaclient.util.request.urlopen') as m_urlopen:
            util.readurl('http://some_url')
        assert 1 == m_urlopen.call_count

    @pytest.mark.parametrize(
        'data', [b'{}', b'not a dict', b'{"caveat_id": "dict"}']
    )
    def test_data_passed_through_unchanged(self, data):
        with mock.patch('uaclient.util.request.urlopen') as m_urlopen:
            util.readurl('http://some_url', data=data)

        assert 1 == m_urlopen.call_count
        req = m_urlopen.call_args[0][0]  # the first positional argument
        assert data == req.data


class TestDisableLogToConsole:
    @pytest.mark.parametrize('caplog_text', [logging.DEBUG], indirect=True)
    def test_no_error_if_console_handler_not_found(self, caplog_text):
        with mock.patch('uaclient.util.logging.getLogger') as m_getlogger:
            m_getlogger.return_value.handlers = []
            with util.disable_log_to_console():
                pass

        assert 'no console handler found' in caplog_text()

    @pytest.mark.parametrize('disable_log', (True, False))
    def test_disable_log_to_console(
        self, logging_sandbox, capsys, disable_log
    ):
        # This test is parameterised so that we are sure that the context
        # manager is suppressing the output, not some other config change

        cli.setup_logging(logging.INFO, logging.INFO)

        if disable_log:
            context_manager = util.disable_log_to_console
        else:
            context_manager = mock.MagicMock

        with context_manager():
            logging.error('test error')
            logging.info('test info')

        out, err = capsys.readouterr()
        combined_output = out + err
        if disable_log:
            assert not combined_output
        else:
            assert 'test error' in combined_output
            assert 'test info' in combined_output

    def test_disable_log_to_console_does_nothing_at_debug_level(
        self, logging_sandbox, capsys
    ):
        cli.setup_logging(logging.DEBUG, logging.DEBUG)

        with util.disable_log_to_console():
            logging.error('test error')
            logging.info('test info')

        out, err = capsys.readouterr()
        combined_output = out + err
        assert 'test error' in combined_output
        assert 'test info' in combined_output


JSON_TEST_PAIRS = (
    ('a', '"a"'),
    (1, '1'),
    ({'a': 1}, '{"a": 1}'),
    # See the note in DatetimeAwareJSONDecoder for why this datetime is in a
    # dict
    (
        {'dt': datetime.datetime(2019, 7, 25, 14, 35, 51)},
        '{"dt": "2019-07-25T14:35:51"}',
    ),
)


class TestDatetimeAwareJSONEncoder:
    @pytest.mark.parametrize('input,out', JSON_TEST_PAIRS)
    def test_encode(self, input, out):
        assert out == json.dumps(input, cls=util.DatetimeAwareJSONEncoder)


class TestDatetimeAwareJSONDecoder:

    # Note that the parameter names are flipped from
    # TestDatetimeAwareJSONEncoder
    @pytest.mark.parametrize('out,input', JSON_TEST_PAIRS)
    def test_encode(self, input, out):
        assert out == json.loads(input, cls=util.DatetimeAwareJSONDecoder)

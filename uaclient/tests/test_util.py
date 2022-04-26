"""Tests related to uaclient.util module."""
import datetime
import json
import logging
import posix
import socket
import subprocess
import urllib
import uuid

import mock
import pytest

from uaclient import cli, exceptions, messages, util

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


class TestGetDictDeltas:
    @pytest.mark.parametrize(
        "value1,value2", (("val1", "val2"), ([1], [2]), ((1, 2), (3, 4)))
    )
    def test_non_dict_diffs_return_new_value(self, value1, value2):
        """When two values differ and are not a dict return the new value."""
        expected = {"key": value2}
        assert expected == util.get_dict_deltas(
            {"key": value1}, {"key": value2}
        )

    def test_diffs_return_new_keys_and_values(self):
        """New keys previously absent will be returned in the delta."""
        expected = {"newkey": "val"}
        assert expected == util.get_dict_deltas(
            {"k": "v"}, {"newkey": "val", "k": "v"}
        )

    def test_diffs_return_dropped_keys_set_dropped(self):
        """Old keys which are now dropped are returned as DROPPED_KEY."""
        expected = {"oldkey": util.DROPPED_KEY, "oldkey2": util.DROPPED_KEY}
        assert expected == util.get_dict_deltas(
            {"oldkey": "v", "k": "v", "oldkey2": {}}, {"k": "v"}
        )

    def test_return_only_keys_which_represent_deltas(self):
        """Only return specific keys which have deltas."""
        orig_dict = {
            "1": "1",
            "2": "orig2",
            "3": {"3.1": "3.1", "3.2": "orig3.2"},
            "4": {"4.1": "4.1"},
        }
        new_dict = {
            "1": "1",
            "2": "new2",
            "3": {"3.1": "3.1", "3.2": "new3.2"},
            "4": {"4.1": "4.1"},
        }
        expected = {"2": "new2", "3": {"3.2": "new3.2"}}
        assert expected == util.get_dict_deltas(orig_dict, new_dict)


class TestIsLTS:
    @pytest.mark.parametrize(
        "series, supported_esm, expected",
        (
            ("xenial", "xenial\nbionic\nfocal", True),
            ("groovy", "xenial\nbionic\nfocal", False),
        ),
    )
    @mock.patch("uaclient.util.subp")
    def test_is_lts_if_distro_info_supported_esm(
        self, subp, series, supported_esm, expected
    ):
        subp.return_value = supported_esm, ""
        # Use __wrapped__ to avoid hitting the lru_cached value across tests
        assert expected is util.is_lts.__wrapped__(series)
        assert [
            mock.call(["/usr/bin/ubuntu-distro-info", "--supported-esm"])
        ] == subp.call_args_list


class TestIsActiveESM:
    @pytest.mark.parametrize(
        "series, is_lts, days_until_esm,expected",
        (
            ("xenial", True, 1, False),
            ("xenial", True, 0, True),
            ("bionic", True, 1, False),
            ("bionic", True, 0, True),
            ("focal", True, 1, False),
            ("focal", True, 0, True),
            ("groovy", False, 0, False),
        ),
    )
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.util.is_lts")
    def test_true_when_supported_esm_release_and_active(
        self, util_is_lts, subp, series, is_lts, days_until_esm, expected
    ):
        """Return True when series is --suported-esm and days until esm < 1."""
        util_is_lts.return_value = is_lts
        subp.return_value = str(days_until_esm), ""

        # Use __wrapped__ to avoid hitting the lru_cached value across tests
        calls = []
        if is_lts:
            calls.append(
                mock.call(
                    [
                        "/usr/bin/ubuntu-distro-info",
                        "--series",
                        series,
                        "-yeol",
                    ]
                )
            )
        assert expected is util.is_active_esm.__wrapped__(series)
        assert calls == subp.call_args_list


class TestIsContainer:
    @mock.patch("uaclient.util.subp")
    def test_true_systemd_detect_virt_success(self, m_subp):
        """Return True when systemd-detect virt exits success."""
        util.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            "",
            "",
        ]
        assert True is util.is_container()
        # Second call for lru_cache test
        util.is_container()
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list

    @mock.patch("uaclient.util.subp")
    def test_true_on_run_container_type(self, m_subp, tmpdir):
        """Return True when /run/container_type exists."""
        util.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            OSError("No systemd-detect-virt utility"),
        ]
        tmpdir.join("container_type").write("")

        assert True is util.is_container(run_path=tmpdir.strpath)
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list

    @mock.patch("uaclient.util.subp")
    def test_true_on_run_systemd_container(self, m_subp, tmpdir):
        """Return True when /run/systemd/container exists."""
        util.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            OSError("No systemd-detect-virt utility"),
        ]
        tmpdir.join("systemd/container").write("", ensure=True)

        assert True is util.is_container(run_path=tmpdir.strpath)
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list

    @mock.patch("uaclient.util.subp")
    def test_false_on_non_sytemd_detect_virt_and_no_runfiles(
        self, m_subp, tmpdir
    ):
        """Return False when sytemd-detect-virt erros and no /run/* files."""
        util.is_container.cache_clear()
        m_subp.side_effect = [
            exceptions.ProcessExecutionError(
                "Failed running command 'ischroot' [exit(1)]"
            ),
            OSError("No systemd-detect-virt utility"),
        ]
        tmpdir.join("systemd/container").write("", ensure=True)

        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            m_exists.return_value = False
            assert False is util.is_container(run_path=tmpdir.strpath)
        calls = [
            mock.call(["ischroot"]),
            mock.call(["systemd-detect-virt", "--quiet", "--container"]),
        ]
        assert calls == m_subp.call_args_list
        exists_calls = [
            mock.call(tmpdir.join("container_type").strpath),
            mock.call(tmpdir.join("systemd/container").strpath),
        ]
        assert exists_calls == m_exists.call_args_list

    @mock.patch("uaclient.util.subp")
    def test_false_on_chroot_system(self, m_subp):
        util.is_container.cache_clear()
        m_subp.return_value = ("", "")
        assert False is util.is_container()

        calls = [mock.call(["ischroot"])]
        assert calls == m_subp.call_args_list


class TestSubp:
    def test_raise_error_on_timeout(self, _subp):
        """When cmd exceeds the timeout raises a TimeoutExpired error."""
        with mock.patch("uaclient.util._subp", side_effect=_subp):
            with pytest.raises(subprocess.TimeoutExpired) as excinfo:
                util.subp(["sleep", "2"], timeout=0)
        msg = "Command '[b'sleep', b'2']' timed out after 0 seconds"
        assert msg == str(excinfo.value)

    @mock.patch("uaclient.util.time.sleep")
    def test_default_do_not_retry_on_failure_return_code(self, m_sleep, _subp):
        """When no retry_sleeps are specified, do not retry failures."""
        with mock.patch("uaclient.util._subp", side_effect=_subp):
            with pytest.raises(exceptions.ProcessExecutionError) as excinfo:
                util.subp(["ls", "--bogus"])

        assert 2 == excinfo.value.exit_code
        assert "" == excinfo.value.stdout
        assert 0 == m_sleep.call_count  # no retries

    @mock.patch("uaclient.util.time.sleep")
    def test_no_error_on_accepted_return_codes(self, m_sleep, _subp):
        """When rcs list includes the exit code, do not raise an error."""
        with mock.patch("uaclient.util._subp", side_effect=_subp):
            out, _ = util.subp(["ls", "--bogus"], rcs=[2])

        assert "" == out
        assert 0 == m_sleep.call_count  # no retries

    @mock.patch("uaclient.util.time.sleep")
    def test_retry_with_specified_sleeps_on_error(self, m_sleep, _subp):
        """When retry_sleeps given, use defined sleeps between each retry."""
        with mock.patch("uaclient.util._subp", side_effect=_subp):
            with pytest.raises(exceptions.ProcessExecutionError) as excinfo:
                util.subp(["ls", "--bogus"], retry_sleeps=[1, 3, 0.4])

        expected_error = "Failed running command 'ls --bogus' [exit(2)]"
        assert expected_error in str(excinfo.value)
        expected_sleeps = [mock.call(1), mock.call(3), mock.call(0.4)]
        assert expected_sleeps == m_sleep.call_args_list

    @mock.patch("uaclient.util.time.sleep")
    def test_retry_doesnt_consume_retry_sleeps(self, m_sleep, _subp):
        """When retry_sleeps given, use defined sleeps between each retry."""
        sleeps = [1, 3, 0.4]
        expected_sleeps = sleeps.copy()
        with mock.patch("uaclient.util._subp", side_effect=_subp):
            with pytest.raises(exceptions.ProcessExecutionError):
                util.subp(["ls", "--bogus"], retry_sleeps=sleeps)

        assert expected_sleeps == sleeps

    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @mock.patch("uaclient.util._subp")
    @mock.patch("uaclient.util.time.sleep")
    def test_retry_logs_remaining_retries(self, m_sleep, m_subp, caplog_text):
        """When retry_sleeps given, use defined sleeps between each retry."""
        sleeps = [1, 3, 0.4]
        m_subp.side_effect = exceptions.ProcessExecutionError(
            "Funky apt %d error"
        )
        with pytest.raises(exceptions.ProcessExecutionError):
            util.subp(["apt", "dostuff"], retry_sleeps=sleeps)

        logs = caplog_text()
        expected_logs = [
            "'Funky apt %d error'. Retrying 3 more times.",
            "'Funky apt %d error'. Retrying 2 more times.",
            "'Funky apt %d error'. Retrying 1 more times.",
        ]
        for log in expected_logs:
            assert log in logs

    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    @pytest.mark.parametrize("capture", [True, False])
    @mock.patch("uaclient.util._subp")
    def test_log_subp_fails_stdout_stderr_capture_toggle(
        self, m_subp, capture, caplog_text
    ):
        """When subp fails, capture the logs in stdout/stderr"""
        out = "Tried downloading file"
        err = "Network error"
        m_subp.side_effect = exceptions.ProcessExecutionError(
            "Serious apt error", stdout=out, stderr=err
        )
        with pytest.raises(exceptions.ProcessExecutionError):
            util.subp(["apt", "nothing"], capture=capture)

        logs = caplog_text()
        expected_logs = ["Stderr: {}".format(err), "Stdout: {}".format(out)]
        for log in expected_logs:
            if capture:
                assert log in logs
            else:
                assert log not in logs


class TestParseOSRelease:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_parse_os_release(self, caplog_text, tmpdir):
        """parse_os_release returns a dict of values from /etc/os-release."""
        release_file = tmpdir.join("os-release")
        release_file.write(OS_RELEASE_XENIAL)
        expected = {
            "BUG_REPORT_URL": "http://bugs.launchpad.net/ubuntu/",
            "HOME_URL": "http://www.ubuntu.com/",
            "ID": "ubuntu",
            "ID_LIKE": "debian",
            "NAME": "Ubuntu",
            "PRETTY_NAME": "Ubuntu 16.04.5 LTS",
            "SUPPORT_URL": "http://help.ubuntu.com/",
            "UBUNTU_CODENAME": "xenial",
            "VERSION": "16.04.5 LTS (Xenial Xerus)",
            "VERSION_CODENAME": "xenial",
            "VERSION_ID": "16.04",
        }
        assert expected == util.parse_os_release(release_file.strpath)
        # Add a 2nd call for lru_cache test
        util.parse_os_release(release_file.strpath)

        os_release_reads = len(
            [
                line
                for line in caplog_text().splitlines()
                if "os-release" in line
            ]
        )
        assert (
            1 == os_release_reads
        ), "lru_cache expected 1 read but found {}".format(os_release_reads)


class TestGetPlatformInfo:
    @mock.patch("uaclient.util.subp")
    @mock.patch("uaclient.util.parse_os_release")
    def test_get_platform_info_error_no_version(self, m_parse, m_subp):
        """get_platform_info errors when it cannot parse os-release."""
        m_parse.return_value = {"VERSION": "junk"}
        with pytest.raises(RuntimeError) as excinfo:
            # Use __wrapped__ to avoid hitting the
            # lru_cached value across tests
            util.get_platform_info.__wrapped__()
        expected_msg = (
            "Could not parse /etc/os-release VERSION: junk (modified to junk)"
        )
        assert expected_msg == str(excinfo.value)

    @pytest.mark.parametrize(
        "series,release,version,os_release_content",
        [
            ("xenial", "16.04", "16.04 LTS (Xenial Xerus)", OS_RELEASE_XENIAL),
            (
                "bionic",
                "18.04",
                "18.04 LTS (Bionic Beaver)",
                OS_RELEASE_BIONIC,
            ),
            ("disco", "19.04", "19.04 (Disco Dingo)", OS_RELEASE_DISCO),
        ],
    )
    def test_get_platform_info_with_version(
        self, series, release, version, os_release_content, tmpdir
    ):
        release_file = tmpdir.join("os-release")
        release_file.write(os_release_content)
        parse_dict = util.parse_os_release(release_file.strpath)

        expected = {
            "arch": "arm64",
            "distribution": "Ubuntu",
            "kernel": "kernel-ver",
            "release": release,
            "series": series,
            "type": "Linux",
            "version": version,
        }

        with mock.patch("uaclient.util.parse_os_release") as m_parse:
            with mock.patch("uaclient.util.os.uname") as m_uname:
                with mock.patch("uaclient.util.subp") as m_subp:
                    m_parse.return_value = parse_dict
                    # (sysname, nodename, release, version, machine)
                    m_uname.return_value = posix.uname_result(
                        ("", "", "kernel-ver", "", "aarch64")
                    )
                    m_subp.return_value = ("arm64\n", "")
                    # Use __wrapped__ to avoid hitting the
                    # lru_cached value across tests
                    assert expected == util.get_platform_info.__wrapped__()


class TestApplyContractOverrides:
    @pytest.mark.parametrize(
        "override_selector,expected_weight",
        (
            ({"selector1": "valueX", "selector2": "valueZ"}, 0),
            ({"selector1": "valueA", "selector2": "valueZ"}, 0),
            ({"selector1": "valueX", "selector2": "valueB"}, 0),
            ({"selector1": "valueA"}, 1),
            ({"selector2": "valueB"}, 2),
            ({"selector1": "valueA", "selector2": "valueB"}, 3),
        ),
    )
    def test_get_override_weight(self, override_selector, expected_weight):
        selector_values = {"selector1": "valueA", "selector2": "valueB"}
        selector_weights = {"selector1": 1, "selector2": 2}
        with mock.patch(
            "uaclient.util.OVERRIDE_SELECTOR_WEIGHTS", selector_weights
        ):
            assert expected_weight == util._get_override_weight(
                override_selector, selector_values
            )

    def test_error_on_non_entitlement_dict(self):
        """Raise a runtime error when seeing invalid dict type."""
        with pytest.raises(RuntimeError) as exc:
            util.apply_contract_overrides({"some": "dict"})
        error = (
            'Expected entitlement access dict. Missing "entitlement" key:'
            " {'some': 'dict'}"
        )
        assert error == str(exc.value)

    @pytest.mark.parametrize("include_overrides", (True, False))
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "ubuntuX"}
    )
    @mock.patch(
        "uaclient.clouds.identity.get_cloud_type", return_value=(None, "")
    )
    def test_return_same_dict_when_no_overrides_match(
        self, _m_cloud_type, _m_platform_info, include_overrides
    ):
        orig_access = {
            "entitlement": {
                "affordances": {"some_affordance": ["ubuntuX"]},
                "directives": {"some_directive": ["ubuntuX"]},
                "obligations": {"some_obligation": False},
            }
        }
        # exactly the same
        expected = {
            "entitlement": {
                "affordances": {"some_affordance": ["ubuntuX"]},
                "directives": {"some_directive": ["ubuntuX"]},
                "obligations": {"some_obligation": False},
            }
        }
        if include_overrides:
            orig_access["entitlement"].update(
                {
                    "series": {
                        "dontMatch": {
                            "affordances": {
                                "some_affordance": ["ubuntuX-series-overriden"]
                            }
                        }
                    },
                    "overrides": [
                        {
                            "selector": {"series": "dontMatch"},
                            "affordances": {
                                "some_affordance": ["ubuntuX-series-overriden"]
                            },
                        },
                        {
                            "selector": {"cloud": "dontMatch"},
                            "affordances": {
                                "some_affordance": ["ubuntuX-cloud-overriden"]
                            },
                        },
                    ],
                }
            )

        util.apply_contract_overrides(orig_access)
        assert expected == orig_access

    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "ubuntuX"}
    )
    def test_missing_keys_are_included(self, _m_platform_info):
        orig_access = {
            "entitlement": {
                "series": {"ubuntuX": {"directives": {"suites": ["ubuntuX"]}}}
            }
        }
        expected = {"entitlement": {"directives": {"suites": ["ubuntuX"]}}}

        util.apply_contract_overrides(orig_access)

        assert expected == orig_access

    @pytest.mark.parametrize(
        "series_selector,cloud_selector,series_cloud_selector,expected_value",
        (
            # apply_overrides_when_only_series_match
            ("no-match", "no-match", "no-match", "old_series_overriden"),
            # series selector is applied over old series override
            ("ubuntuX", "no-match", "no-match", "series_overriden"),
            # cloud selector is applied over series override
            ("no-match", "cloudX", "no-match", "cloud_overriden"),
            # cloud selector is applied over series selector
            ("ubuntuX", "cloudX", "no-match", "cloud_overriden"),
            # cloud and series together are applied over others
            ("ubuntuX", "cloudX", "cloudX", "both_overriden"),
        ),
    )
    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "ubuntuX"}
    )
    @mock.patch(
        "uaclient.clouds.identity.get_cloud_type",
        return_value=("cloudX", None),
    )
    def test_applies_contract_overrides_respecting_weight(
        self,
        _m_cloud_type,
        _m_platform_info,
        series_selector,
        cloud_selector,
        series_cloud_selector,
        expected_value,
    ):
        """Apply the expected overrides to orig_access dict when called."""
        orig_access = {
            "entitlement": {
                "affordances": {"some_affordance": ["original_affordance"]},
                "series": {
                    "ubuntuX": {
                        "affordances": {
                            "some_affordance": ["old_series_overriden"]
                        }
                    }
                },
                "overrides": [
                    {
                        "selector": {"series": series_selector},
                        "affordances": {
                            "some_affordance": ["series_overriden"]
                        },
                    },
                    {
                        "selector": {"cloud": cloud_selector},
                        "affordances": {
                            "some_affordance": ["cloud_overriden"]
                        },
                    },
                    {
                        "selector": {
                            "series": series_selector,
                            "cloud": series_cloud_selector,
                        },
                        "affordances": {"some_affordance": ["both_overriden"]},
                    },
                ],
            }
        }

        expected = {
            "entitlement": {
                "affordances": {"some_affordance": [expected_value]}
            }
        }

        util.apply_contract_overrides(orig_access)
        assert orig_access == expected

    @mock.patch(
        "uaclient.util.get_platform_info", return_value={"series": "ubuntuX"}
    )
    @mock.patch(
        "uaclient.clouds.identity.get_cloud_type",
        return_value=("cloudX", None),
    )
    def test_different_overrides_applied_together(
        self, _m_cloud_type, _m_platform_info
    ):
        """Apply different overrides from different matching selectors."""
        orig_access = {
            "entitlement": {
                "affordances": {"some_affordance": ["original_affordance"]},
                "directives": {"some_directive": ["original_directive"]},
                "obligations": {"some_obligation": False},
                "series": {
                    "ubuntuX": {
                        "affordances": {
                            "new_affordance": ["new_affordance_value"]
                        }
                    }
                },
                "overrides": [
                    {
                        "selector": {"series": "ubuntuX"},
                        "affordances": {
                            "some_affordance": ["series_overriden"]
                        },
                    },
                    {
                        "selector": {"cloud": "cloudX"},
                        "directives": {"some_directive": ["cloud_overriden"]},
                    },
                    {
                        "selector": {"series": "ubuntuX", "cloud": "cloudX"},
                        "obligations": {
                            "new_obligation": True,
                            "some_obligation": True,
                        },
                    },
                ],
            }
        }

        expected = {
            "entitlement": {
                "affordances": {
                    "new_affordance": ["new_affordance_value"],
                    "some_affordance": ["series_overriden"],
                },
                "directives": {"some_directive": ["cloud_overriden"]},
                "obligations": {
                    "new_obligation": True,
                    "some_obligation": True,
                },
            }
        }

        util.apply_contract_overrides(orig_access)
        assert orig_access == expected


class TestGetMachineId:
    def test_get_machine_id_from_config(self, FakeConfig):
        cfg = FakeConfig.for_attached_machine()
        value = util.get_machine_id(cfg)
        assert "test_machine_id" == value

    def test_get_machine_id_from_etc_machine_id(self, FakeConfig, tmpdir):
        """Presence of /etc/machine-id is returned if it exists."""
        etc_machine_id = tmpdir.join("etc-machine-id")
        assert "/etc/machine-id" == util.ETC_MACHINE_ID
        etc_machine_id.write("etc-machine-id")
        cfg = FakeConfig()
        with mock.patch(
            "uaclient.util.ETC_MACHINE_ID", etc_machine_id.strpath
        ):
            value = util.get_machine_id(cfg)
            # Test lru_cache caches /etc/machine-id from first read
            etc_machine_id.write("does-not-change")
            cached_value = util.get_machine_id(cfg)
            assert value == cached_value
        assert "etc-machine-id" == value

    def test_get_machine_id_from_var_lib_dbus_machine_id(
        self, FakeConfig, tmpdir
    ):
        """fallback to /var/lib/dbus/machine-id"""
        etc_machine_id = tmpdir.join("etc-machine-id")
        dbus_machine_id = tmpdir.join("dbus-machine-id")
        assert "/var/lib/dbus/machine-id" == util.DBUS_MACHINE_ID
        dbus_machine_id.write("dbus-machine-id")
        cfg = FakeConfig()
        with mock.patch(
            "uaclient.util.DBUS_MACHINE_ID", dbus_machine_id.strpath
        ):
            with mock.patch(
                "uaclient.util.ETC_MACHINE_ID", etc_machine_id.strpath
            ):
                value = util.get_machine_id(cfg)
        assert "dbus-machine-id" == value

    def test_get_machine_id_uses_machine_id_from_data_dir(
        self, FakeConfig, tmpdir
    ):
        """When no machine-id is found, use machine-id from data_dir."""
        data_machine_id = tmpdir.mkdir("private").join("machine-id")
        data_machine_id.write("data-machine-id")

        cfg = FakeConfig()

        def fake_exists(path):
            return bool(path == data_machine_id.strpath)

        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            m_exists.side_effect = fake_exists
            value = util.get_machine_id(cfg)
        assert "data-machine-id" == value

    def test_get_machine_id_create_machine_id_in_data_dir(
        self, FakeConfig, tmpdir
    ):
        """When no machine-id is found, create one in data_dir using uuid4."""
        data_machine_id = tmpdir.mkdir("private").join("machine-id")

        cfg = FakeConfig()
        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            with mock.patch("uaclient.util.uuid.uuid4") as m_uuid4:
                m_exists.return_value = False
                m_uuid4.return_value = uuid.UUID(
                    "0123456789abcdef0123456789abcdef"
                )
                value = util.get_machine_id(cfg)
        assert "01234567-89ab-cdef-0123-456789abcdef" == value
        assert "01234567-89ab-cdef-0123-456789abcdef" == data_machine_id.read()

    @pytest.mark.parametrize("empty_value", ["", "\n"])
    def test_fallback_used_if_all_other_files_are_empty(
        self, FakeConfig, tmpdir, empty_value
    ):
        data_machine_id = tmpdir.mkdir("private").join("machine-id")
        cfg = FakeConfig().for_attached_machine(
            machine_token={"some": "thing"}
        )
        # Need to initialize the property with a noop,
        # so load_file is not called after mocked
        cfg.machine_token
        with mock.patch("uaclient.util.os.path.exists") as m_exists:
            m_exists.return_value = True
            with mock.patch(
                "uaclient.util.load_file", return_value=empty_value
            ):
                with mock.patch("uaclient.util.uuid.uuid4") as m_uuid4:
                    m_uuid4.return_value = uuid.UUID(
                        "0123456789abcdef0123456789abcdef"
                    )
                    value = util.get_machine_id(cfg)
        assert "01234567-89ab-cdef-0123-456789abcdef" == value
        assert "01234567-89ab-cdef-0123-456789abcdef" == data_machine_id.read()


class TestIsServiceUrl:
    @pytest.mark.parametrize(
        "url,is_valid",
        (
            ("http://asdf", True),
            ("http://asdf/", True),
            ("asdf", False),
            ("http://host:port", False),
            ("http://asdf:1234", True),
        ),
    )
    def test_is_valid_url(self, url, is_valid):
        ret = util.is_service_url(url)
        assert is_valid is ret


class TestReadurl:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    @pytest.mark.parametrize(
        "headers,data,method,url,response,expected_logs",
        (
            (
                {},
                None,
                None,
                "http://some_url",
                None,
                [
                    "URL [GET]: http://some_url, headers: {}, data: None",
                    "URL [GET] response: http://some_url, headers: {},"
                    " data: response\n",
                ],
            ),
            # AWS PRO redacts IMDSv2 token
            (
                {
                    "X-aws-ec2-metadata-token-ttl-seconds": "21600",
                    "X-aws-ec2-metadata-token": "SEKRET",
                },
                None,
                "PUT",
                "http://169.254.169.254/latest/api/token",
                b"SECRET==",
                [
                    "URL [PUT]: http://169.254.169.254/latest/api/token,"
                    " headers: {'X-aws-ec2-metadata-token': '<REDACTED>',"
                    " 'X-aws-ec2-metadata-token-ttl-seconds': '21600'}",
                    "URL [PUT] response:"
                    " http://169.254.169.254/latest/api/token, headers:"
                    " {'X-aws-ec2-metadata-token': '<REDACTED>',"
                    " 'X-aws-ec2-metadata-token-ttl-seconds': '21600'},"
                    " data: <REDACTED>\n",
                ],
            ),
            (
                {"key1": "Bearcat", "Authorization": "Bearer SEKRET"},
                b"{'token': 'HIDEME', 'tokenInfo': 'SHOWME'}",
                None,
                "http://some_url",
                b"{'machineToken': 'HIDEME', 'machineTokenInfo': 'SHOWME'}",
                [
                    "URL [POST]: http://some_url, headers: {'Authorization':"
                    " 'Bearer <REDACTED>', 'key1': 'Bearcat'}, data:"
                    " {'token': '<REDACTED>', 'tokenInfo': 'SHOWME'}",
                    "URL [POST] response: http://some_url, headers:"
                    " {'Authorization': 'Bearer <REDACTED>', 'key1': 'Bearcat'"
                    "}, data: {'machineToken': '<REDACTED>',"
                    " 'machineTokenInfo': 'SHOWME'}",
                ],
            ),
        ),
    )
    @mock.patch("uaclient.util.request.urlopen")
    def test_readurl_redacts_call_and_response(
        self,
        urlopen,
        headers,
        data,
        method,
        url,
        response,
        expected_logs,
        caplog_text,
    ):
        """Log and redact sensitive data from logs for url interactions."""

        class FakeHTTPResponse:
            def __init__(self, headers, content):
                self.headers = headers
                self._content = content

            def read(self):
                return self._content

        if not response:
            response = b"response"
        urlopen.return_value = FakeHTTPResponse(
            headers=headers, content=response
        )
        util.readurl(url, method=method, headers=headers, data=data)
        logs = caplog_text()
        for log in expected_logs:
            assert log in logs

    @pytest.mark.parametrize("timeout", (None, 1))
    def test_simple_call_with_url_and_timeout_works(self, timeout):
        with mock.patch("uaclient.util.request.urlopen") as m_urlopen:
            if timeout:
                util.readurl("http://some_url", timeout=timeout)
            else:
                util.readurl("http://some_url")
        assert [
            mock.call(mock.ANY, timeout=timeout)
        ] == m_urlopen.call_args_list

    def test_call_with_timeout(self):
        with mock.patch("uaclient.util.request.urlopen") as m_urlopen:
            util.readurl("http://some_url")
        assert 1 == m_urlopen.call_count

    @pytest.mark.parametrize(
        "data", [b"{}", b"not a dict", b'{"caveat_id": "dict"}']
    )
    def test_data_passed_through_unchanged(self, data):
        with mock.patch("uaclient.util.request.urlopen") as m_urlopen:
            util.readurl("http://some_url", data=data)

        assert 1 == m_urlopen.call_count
        req = m_urlopen.call_args[0][0]  # the first positional argument
        assert data == req.data


class TestDisableLogToConsole:
    @pytest.mark.parametrize("caplog_text", [logging.DEBUG], indirect=True)
    def test_no_error_if_console_handler_not_found(self, caplog_text):
        with mock.patch("uaclient.util.logging.getLogger") as m_getlogger:
            m_getlogger.return_value.handlers = []
            with util.disable_log_to_console():
                pass

        assert "no console handler found" in caplog_text()

    @pytest.mark.parametrize("disable_log", (True, False))
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
            logging.error("test error")
            logging.info("test info")

        out, err = capsys.readouterr()
        combined_output = out + err
        if disable_log:
            assert not combined_output
        else:
            assert "test error" in combined_output
            assert "test info" in combined_output

    def test_disable_log_to_console_does_nothing_at_debug_level(
        self, logging_sandbox, capsys
    ):
        cli.setup_logging(logging.DEBUG, logging.DEBUG)

        with util.disable_log_to_console():
            logging.error("test error")
            logging.info("test info")

        out, err = capsys.readouterr()
        combined_output = out + err
        assert "test error" in combined_output
        assert "test info" in combined_output


JSON_TEST_PAIRS = (
    ("a", '"a"'),
    (1, "1"),
    ({"a": 1}, '{"a": 1}'),
    # See the note in DatetimeAwareJSONDecoder for why this datetime is in a
    # dict
    (
        {
            "dt": datetime.datetime(
                2019, 7, 25, 14, 35, 51, tzinfo=datetime.timezone.utc
            )
        },
        '{"dt": "2019-07-25T14:35:51+00:00"}',
    ),
)


class TestDatetimeAwareJSONEncoder:
    @pytest.mark.parametrize("input,out", JSON_TEST_PAIRS)
    def test_encode(self, input, out):
        assert out == json.dumps(input, cls=util.DatetimeAwareJSONEncoder)


class TestDatetimeAwareJSONDecoder:

    # Note that the parameter names are flipped from
    # TestDatetimeAwareJSONEncoder
    @pytest.mark.parametrize("out,input", JSON_TEST_PAIRS)
    def test_encode(self, input, out):
        assert out == json.loads(input, cls=util.DatetimeAwareJSONDecoder)


@mock.patch("builtins.input")
class TestPromptForConfirmation:
    @pytest.mark.parametrize(
        "return_value,user_input",
        [(True, yes_input) for yes_input in ["y", "Y", "yes", "YES", "YeS"]]
        + [
            (False, no_input)
            for no_input in ["n", "N", "no", "NO", "No", "asdf", "", "\nfoo\n"]
        ],
    )
    def test_input_conversion(self, m_input, return_value, user_input):
        m_input.return_value = user_input
        assert return_value == util.prompt_for_confirmation()

    @pytest.mark.parametrize(
        "assume_yes,message,input_calls",
        [
            (True, "message ignored on assume_yes=True", []),
            (False, "", [mock.call("Are you sure? (y/N) ")]),
            (False, "Custom yep? (y/N) ", [mock.call("Custom yep? (y/N) ")]),
        ],
    )
    def test_prompt_text(self, m_input, assume_yes, message, input_calls):
        util.prompt_for_confirmation(msg=message, assume_yes=assume_yes)

        assert input_calls == m_input.call_args_list


class TestIsConfigValueTrue:
    @pytest.mark.parametrize(
        "config_dict, return_val",
        [
            ({}, False),
            ({}, False),
            (None, False),
            ({None}, False),
            ({"allow_beta": "true"}, True),
            ({"allow_beta": "True"}, True),
            ({"allow_beta": "false"}, False),
            ({"allow_beta": "False"}, False),
        ],
    )
    def test_is_config_value_true(self, config_dict, return_val, FakeConfig):
        cfg = FakeConfig()
        cfg.override_features(config_dict)
        actual_val = util.is_config_value_true(
            config=cfg.cfg, path_to_value="features.allow_beta"
        )
        assert return_val == actual_val

    @pytest.mark.parametrize(
        "config_dict, key_val",
        [
            ({"allow_beta": "tru"}, "tru"),
            ({"allow_beta": "Tre"}, "Tre"),
            ({"allow_beta": "flse"}, "flse"),
            ({"allow_beta": "Fale"}, "Fale"),
        ],
    )
    def test_exception_is_config_value_true(
        self, config_dict, key_val, FakeConfig
    ):
        path_to_value = "features.allow_beta"
        cfg = FakeConfig()
        cfg.override_features(config_dict)
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            util.is_config_value_true(
                config=cfg.cfg, path_to_value=path_to_value
            )

        expected_msg = messages.ERROR_INVALID_CONFIG_VALUE.format(
            path_to_value=path_to_value,
            expected_value="boolean string: true or false",
            value=key_val,
        )
        assert expected_msg == str(excinfo.value)


class TestRedactSensitiveLogs:
    @pytest.mark.parametrize(
        "raw_log,expected",
        (
            ("Super valuable", "Super valuable"),
            (
                "Hi 'Bearer not the droids you are looking for', data",
                "Hi 'Bearer <REDACTED>', data",
            ),
            (
                "Hi 'Bearer not the droids you are looking for', data",
                "Hi 'Bearer <REDACTED>', data",
            ),
            (
                "Executed with sys.argv: ['/usr/bin/ua', 'attach', 'SEKRET']",
                "Executed with sys.argv:"
                " ['/usr/bin/ua', 'attach', '<REDACTED>']",
            ),
            (
                "'resourceTokens': [{'token': 'SEKRET', 'type': 'cc-eal'}]'",
                "'resourceTokens':"
                " [{'token': '<REDACTED>', 'type': 'cc-eal'}]'",
            ),
            (
                "'machineToken': 'SEKRET', 'machineTokenInfo': 'blah'",
                "'machineToken': '<REDACTED>', 'machineTokenInfo': 'blah'",
            ),
            (
                "Failed running command '/usr/lib/apt/apt-helper download-file"
                "https://bearer:S3-Kr3T@esm.ubuntu.com/infra/ubuntu/pool/ "
                "[exit(100)]. Message: Download of file failed"
                " pkgAcquire::Run (13: Permission denied)",
                "Failed running command '/usr/lib/apt/apt-helper download-file"
                "https://bearer:<REDACTED>@esm.ubuntu.com/infra/ubuntu/pool/ "
                "[exit(100)]. Message: Download of file failed"
                " pkgAcquire::Run (13: Permission denied)",
            ),
            (
                "/snap/bin/canonical-livepatch enable S3-Kr3T, foobar",
                "/snap/bin/canonical-livepatch enable <REDACTED> foobar",
            ),
            (
                "Contract value for 'resourceToken' changed to S3kR3T",
                "Contract value for 'resourceToken' changed to <REDACTED>",
            ),
            (
                "data: {'contractToken': 'SEKRET', "
                "'contractTokenInfo':{'expiry'}}",
                "data: {'contractToken': '<REDACTED>', "
                "'contractTokenInfo':{'expiry'}}",
            ),
            (
                "data: {'resourceToken': 'SEKRET', "
                "'entitlement': {'affordances':'blah blah' }}",
                "data: {'resourceToken': '<REDACTED>', "
                "'entitlement': {'affordances':'blah blah' }}",
            ),
            (
                "https://contracts.canonical.com/v1/resources/livepatch"
                "?token=SEKRET: invalid token",
                "https://contracts.canonical.com/v1/resources/livepatch"
                "?token=<REDACTED> invalid token",
            ),
            (
                'data: {"identityToken": "SEket.124-_ys"}',
                'data: {"identityToken": "<REDACTED>"}',
            ),
            (
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
            ),
            (
                "response: "
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: none",
                "response: "
                "http://metadata/computeMetadata/v1/instance/service-accounts/"
                "default/identity?audience=contracts.canon, data: <REDACTED>",
            ),
        ),
    )
    def test_redact_all_matching_regexs(self, raw_log, expected):
        """Redact all sensitive matches from log messages."""
        assert expected == util.redact_sensitive_logs(raw_log)


class TestParseRFC3339Date:
    @pytest.mark.parametrize(
        "datestring,expected",
        [
            (
                "2001-02-03T04:05:06",
                datetime.datetime(
                    2001, 2, 3, 4, 5, 6, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2001-02-03T04:05:06.123456",
                datetime.datetime(
                    2001, 2, 3, 4, 5, 6, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2001-02-03T04:05:06Z",
                datetime.datetime(
                    2001, 2, 3, 4, 5, 6, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2001-02-03T04:05:06-08:00",
                datetime.datetime(
                    2001,
                    2,
                    3,
                    4,
                    5,
                    6,
                    tzinfo=datetime.timezone(-datetime.timedelta(hours=8)),
                ),
            ),
            (
                "2001-02-03T04:05:06+03:00",
                datetime.datetime(
                    2001,
                    2,
                    3,
                    4,
                    5,
                    6,
                    tzinfo=datetime.timezone(datetime.timedelta(hours=3)),
                ),
            ),
            (
                "2021-05-07T09:46:37.791Z",
                datetime.datetime(
                    2021, 5, 7, 9, 46, 37, tzinfo=datetime.timezone.utc
                ),
            ),
            (
                "2021-05-28T14:42:37.944609726-04:00",
                datetime.datetime(
                    2021,
                    5,
                    28,
                    14,
                    42,
                    37,
                    tzinfo=datetime.timezone(-datetime.timedelta(hours=4)),
                ),
            ),
        ],
    )
    def test_parse_rfc3339_date_from_golang(self, datestring, expected):
        """
        Check we are able to parse dates generated by golang's MarshalJSON
        """
        assert expected == util.parse_rfc3339_date(datestring)


class TestConfigureWebProxy:
    @pytest.mark.parametrize(
        "http_proxy,https_proxy,m_environ,expected_environ",
        (
            (
                None,
                None,
                {},
                {
                    "NO_PROXY": "169.254.169.254,[fd00:ec2::254],metadata",
                    "no_proxy": "169.254.169.254,[fd00:ec2::254],metadata",
                },
            ),
            (
                "http://proxy",
                "https://proxy",
                {"no_proxy": "a,10.0.0.1"},
                {
                    "NO_PROXY": "10.0.0.1,169.254.169.254,[fd00:ec2::254],a,metadata",  # noqa
                    "no_proxy": "10.0.0.1,169.254.169.254,[fd00:ec2::254],a,metadata",  # noqa
                },
            ),
            (
                "http://proxy",
                "https://proxy",
                {"NO_PROXY": "a,169.254.169.254"},
                {
                    "NO_PROXY": "169.254.169.254,[fd00:ec2::254],a,metadata",
                    "no_proxy": "169.254.169.254,[fd00:ec2::254],a,metadata",
                },
            ),
        ),
    )
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_no_proxy_set_in_environ(
        self, m_open, http_proxy, https_proxy, m_environ, expected_environ
    ):
        with mock.patch.dict(util.os.environ, m_environ, clear=True):
            util.configure_web_proxy(
                http_proxy=http_proxy, https_proxy=https_proxy
            )
            assert expected_environ == util.os.environ


class TestValidateProxy:
    @pytest.mark.parametrize(
        "proxy", ["invalidurl", "htp://wrongscheme", "http//missingcolon"]
    )
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_fails_on_invalid_url(self, m_open, proxy):
        """
        Check that invalid urls are rejected with the correct message
        and that we don't even attempt to use them
        """
        with pytest.raises(exceptions.UserFacingError) as e:
            util.validate_proxy("http", proxy, "http://example.com")

        assert (
            e.value.msg
            == messages.NOT_SETTING_PROXY_INVALID_URL.format(proxy=proxy).msg
        )

    @pytest.mark.parametrize(
        "protocol, proxy, test_url",
        [
            ("http", "http://localhost:1234", "http://example.com"),
            ("https", "http://localhost:1234", "https://example.com"),
            ("https", "https://localhost:1234", "https://example.com"),
        ],
    )
    @mock.patch("urllib.request.Request")
    @mock.patch("urllib.request.ProxyHandler")
    @mock.patch("urllib.request.build_opener")
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_calls_open_on_valid_url(
        self,
        m_open,
        m_build_opener,
        m_proxy_handler,
        m_request,
        protocol,
        proxy,
        test_url,
    ):
        """
        Check that we attempt to use a valid url as a proxy
        Also check that we return the proxy value when the open call succeeds
        """
        m_build_opener.return_value = urllib.request.OpenerDirector()
        ret = util.validate_proxy(protocol, proxy, test_url)

        assert [mock.call(test_url, method="HEAD")] == m_request.call_args_list
        assert [mock.call({protocol: proxy})] == m_proxy_handler.call_args_list
        assert 1 == m_build_opener.call_count
        assert 1 == m_open.call_count

        assert proxy == ret

    @pytest.mark.parametrize(
        "open_side_effect, expected_message",
        [
            (socket.timeout(0, "timeout"), "[Errno 0] timeout"),
            (urllib.error.URLError("reason"), "reason"),
        ],
    )
    @mock.patch("urllib.request.OpenerDirector.open")
    def test_fails_when_open_fails(
        self, m_open, open_side_effect, expected_message, caplog_text
    ):
        """
        Check that we return the appropriate error when the proxy doesn't work
        """
        m_open.side_effect = open_side_effect
        with pytest.raises(exceptions.UserFacingError) as e:
            util.validate_proxy(
                "http", "http://localhost:1234", "http://example.com"
            )

        assert (
            e.value.msg
            == messages.NOT_SETTING_PROXY_NOT_WORKING.format(
                proxy="http://localhost:1234"
            ).msg
        )

        assert (
            messages.ERROR_USING_PROXY.format(
                proxy="http://localhost:1234",
                test_url="http://example.com",
                error=expected_message,
            )
            in caplog_text()
        )


class TestHandleUnicodeCharacters:
    @pytest.mark.parametrize(
        "encoding", ((None), ("utf-8"), ("UTF-8"), ("test"))
    )
    @pytest.mark.parametrize(
        "message,modified_message",
        (
            (messages.OKGREEN_CHECK + " test", "test"),
            (messages.FAIL_X + " fail", "fail"),
            ("\u2014 blah", "- blah"),
        ),
    )
    def test_handle_unicode_characters(
        self, message, modified_message, encoding
    ):
        expected_message = message
        if encoding is None or encoding.upper() != "UTF-8":
            expected_message = modified_message

        with mock.patch("sys.stdout") as m_stdout:
            type(m_stdout).encoding = mock.PropertyMock(return_value=encoding)
            assert expected_message == util.handle_unicode_characters(message)


class TestShouldReboot:
    @pytest.mark.parametrize("path_exists", ((True), (False)))
    @mock.patch("os.path.exists")
    def test_should_reboot_when_no_installed_pkgs_provided(
        self, m_path, path_exists
    ):
        m_path.return_value = path_exists
        assert path_exists == util.should_reboot()
        assert 1 == m_path.call_count

    @mock.patch("os.path.exists")
    @mock.patch("uaclient.util.load_file")
    def test_should_reboot_when_no_reboot_required_pkgs_exist(
        self, m_load_file, m_path
    ):
        installed_pkgs = set(["test"])
        m_path.return_value = True
        m_load_file.side_effect = FileNotFoundError()

        assert util.should_reboot(installed_pkgs)
        assert 1 == m_path.call_count
        assert 1 == m_load_file.call_count

    @pytest.mark.parametrize(
        "installed_pkgs,installed_pkgs_regex,reboot_required_pkgs,"
        "expected_ret",
        (
            (set(["a", "b", "c"]), None, "", False),
            (set(["a", "b", "c"]), None, "a", True),
            (set(["a", "b", "c"]), None, "a\ne", True),
            (set(["a", "b", "c"]), None, "d\ne", False),
            (set(["a", "b", "c"]), set(["t.."]), "a\ne", True),
            (set(["a", "b", "c"]), set(["t.."]), "one\ntwo", True),
            (None, set(["^t..$"]), "one\ntwo", True),
            (None, set(["^t..$"]), "one\nthree", False),
            (None, None, "a\ne", True),
        ),
    )
    @mock.patch("os.path.exists")
    @mock.patch("uaclient.util.load_file")
    def test_should_reboot_when_reboot_required_pkgs_exist(
        self,
        m_load_file,
        m_path,
        installed_pkgs,
        installed_pkgs_regex,
        reboot_required_pkgs,
        expected_ret,
    ):
        m_path.return_value = True
        m_load_file.return_value = reboot_required_pkgs
        assert expected_ret == util.should_reboot(
            installed_pkgs=installed_pkgs,
            installed_pkgs_regex=installed_pkgs_regex,
        )

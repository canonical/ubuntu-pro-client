import copy
import datetime
import itertools
import json
import logging
import os
import stat

import mock
import pytest

from uaclient import apt, exceptions, messages, util, yaml
from uaclient.config import (
    PRIVATE_SUBDIR,
    UA_CONFIGURABLE_KEYS,
    VALID_UA_CONFIG_KEYS,
    DataPath,
    get_config_path,
    parse_config,
)
from uaclient.conftest import FakeNotice
from uaclient.defaults import DEFAULT_CONFIG_FILE
from uaclient.entitlements import valid_services
from uaclient.entitlements.entitlement_status import ApplicationStatus
from uaclient.files import notices
from uaclient.files.notices import NoticesManager
from uaclient.util import depth_first_merge_overlay_dict

KNOWN_DATA_PATHS = (
    ("machine-access-cis", "machine-access-cis.json"),
    ("instance-id", "instance-id"),
)
M_PATH = "uaclient.entitlements."


@pytest.fixture
def all_resources_available(FakeConfig):
    resources = [
        {"name": name, "available": True}
        for name in valid_services(cfg=FakeConfig(), allow_beta=True)
    ]
    return resources


@pytest.fixture
def all_resources_entitled(FakeConfig):
    resources = [
        {"type": name, "entitled": True}
        for name in valid_services(cfg=FakeConfig(), allow_beta=True)
    ]
    return resources


@pytest.fixture
def no_resources_entitled(FakeConfig):
    resources = [
        {"type": name, "entitled": False}
        for name in valid_services(cfg=FakeConfig(), allow_beta=True)
    ]
    return resources


@pytest.fixture
def resp_only_fips_resource_available(FakeConfig):
    resources = [
        {"name": name, "available": name == "fips"}
        for name in valid_services(cfg=FakeConfig(), allow_beta=True)
    ]
    return resources


class TestNotices:
    @pytest.mark.parametrize(
        "notices,expected",
        (
            ([], ()),
            (
                [[FakeNotice.a2, "a1"]],
                ["a1"],
            ),
            (
                [
                    [FakeNotice.a, "a1"],
                    [FakeNotice.a2, "a2"],
                ],
                [
                    "a1",
                    "a2",
                ],
            ),
            (
                [
                    [FakeNotice.a, "a1"],
                    [FakeNotice.a, "a1"],
                ],
                [
                    "a1",
                ],
            ),
        ),
    )
    def test_add_notice_avoids_duplicates(
        self,
        notices,
        expected,
    ):
        notice = NoticesManager()
        assert [] == notice.list()
        for notice_ in notices:
            notice.add(*notice_)
        if notices:
            assert expected == notice.list()
        else:
            assert [] == notice.list()

    @pytest.mark.parametrize(
        "_notices",
        (
            ([]),
            ([[FakeNotice.a]]),
            (
                [
                    [FakeNotice.a],
                    [FakeNotice.a2],
                ]
            ),
        ),
    )
    @mock.patch("uaclient.util.we_are_currently_root", return_value=False)
    def test_add_notice_fails_as_nonroot(
        self,
        m_we_are_currently_root,
        _notices,
    ):
        assert [] == notices.list()
        for notice_ in _notices:
            notices.add(*notice_)
        assert [] == notices.list()

    @pytest.mark.parametrize(
        "notices_,removes,expected",
        (
            ([], [FakeNotice.a], []),
            (
                [[FakeNotice.a2]],
                [FakeNotice.a2],
                [],
            ),
            (
                [
                    [FakeNotice.a],
                    [FakeNotice.a2],
                ],
                [FakeNotice.a],
                ["notice_a2"],
            ),
            (
                [
                    [FakeNotice.a],
                    [FakeNotice.a2],
                    [FakeNotice.b],
                ],
                [
                    FakeNotice.a,
                    FakeNotice.a2,
                ],
                ["notice_b"],
            ),
        ),
    )
    def test_remove_notice_removes_matching(
        self,
        notices_,
        removes,
        expected,
    ):

        for notice_ in notices_:
            notices.add(*notice_)
        for label in removes:
            notices.remove(label)
        assert expected == notices.list()


class TestEntitlements:
    def test_entitlements_property_keyed_by_entitlement_name(
        self, tmpdir, FakeConfig, all_resources_available
    ):
        """Return machine_token resourceEntitlements, keyed by name."""
        cfg = FakeConfig()
        token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True},
                        {"type": "entitlement2", "entitled": True},
                    ]
                }
            },
        }
        cfg.machine_token_file.write(token)
        expected = {
            "entitlement1": {
                "entitlement": {"entitled": True, "type": "entitlement1"}
            },
            "entitlement2": {
                "entitlement": {"entitled": True, "type": "entitlement2"}
            },
        }
        assert expected == cfg.machine_token_file.entitlements

    def test_entitlements_uses_resource_token_from_machine_token(
        self, FakeConfig, all_resources_available
    ):
        """Include entitlement-specific resourceTokens from machine_token"""
        cfg = FakeConfig()
        token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True},
                        {"type": "entitlement2", "entitled": True},
                    ]
                }
            },
            "resourceTokens": [
                {"type": "entitlement1", "token": "ent1-token"},
                {"type": "entitlement2", "token": "ent2-token"},
            ],
        }
        cfg.machine_token_file.write(token)
        expected = {
            "entitlement1": {
                "entitlement": {"entitled": True, "type": "entitlement1"},
                "resourceToken": "ent1-token",
            },
            "entitlement2": {
                "entitlement": {"entitled": True, "type": "entitlement2"},
                "resourceToken": "ent2-token",
            },
        }
        assert expected == cfg.machine_token_file.entitlements


class TestAccounts:
    def test_accounts_returns_none_when_no_cached_account_value(
        self, tmpdir, FakeConfig, all_resources_available
    ):
        """Config.accounts property returns an empty list when no cache."""
        cfg = FakeConfig()

        assert cfg.machine_token_file.account is None

    @pytest.mark.usefixtures("all_resources_available")
    def test_accounts_extracts_account_key_from_machine_token_cache(
        self, all_resources_available, tmpdir, FakeConfig
    ):
        """Use machine_token cached accountInfo when no accounts cache."""
        cfg = FakeConfig()
        accountInfo = {"id": "1", "name": "accountname"}

        cfg.machine_token_file.write(
            {
                "availableResources": all_resources_available,
                "machineTokenInfo": {"accountInfo": accountInfo},
            },
        )

        assert accountInfo == cfg.machine_token_file.account


class TestDataPath:
    def test_data_path_returns_data_dir_path_without_key(self, FakeConfig):
        """The data_path method returns the data_dir when key is absent."""
        cfg = FakeConfig({"data_dir": "/my/dir"})
        assert "/my/dir/{}".format(PRIVATE_SUBDIR) == cfg.data_path()

    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_data_path_returns_file_path_with_defined_data_paths(
        self, key, path_basename, FakeConfig
    ):
        """When key is defined in Config.data_paths return data_path value."""
        cfg = FakeConfig({"data_dir": "/my/dir"})
        private_path = "/my/dir/{}/{}".format(PRIVATE_SUBDIR, path_basename)
        assert private_path == cfg.data_path(key=key)

    @pytest.mark.parametrize(
        "key,path_basename", (("notHere", "notHere"), ("anything", "anything"))
    )
    def test_data_path_returns_file_path_with_undefined_data_paths(
        self, key, path_basename, FakeConfig
    ):
        """When key is not in Config.data_paths the key is used to data_dir"""
        cfg = FakeConfig({"data_dir": "/my/d"})
        assert "/my/d/{}/{}".format(PRIVATE_SUBDIR, key) == cfg.data_path(
            key=key
        )

    def test_data_path_returns_public_path_for_public_datapath(
        self, FakeConfig
    ):
        cfg = FakeConfig({"data_dir": "/my/d"})
        cfg.data_paths["test_path"] = DataPath("test_path", False, False)
        assert "/my/d/test_path" == cfg.data_path("test_path")


CFG_BASE_CONTENT = """\
# Ubuntu Pro client config file.
# If you modify this file, run "pro refresh config" to ensure changes are
# picked up by Ubuntu Pro client.

contract_url: https://contracts.canonical.com
daemon_log_file: /var/log/ubuntu-advantage-daemon.log
data_dir: /var/lib/ubuntu-advantage
log_file: /var/log/ubuntu-advantage.log
log_level: debug
security_url: https://ubuntu.com/security
timer_log_file: /var/log/ubuntu-advantage-timer.log
"""

CFG_FEATURES_CONTENT = """\
# Ubuntu Pro client config file.
# If you modify this file, run "pro refresh config" to ensure changes are
# picked up by Ubuntu Pro client.

contract_url: https://contracts.canonical.com
daemon_log_file: /var/log/ubuntu-advantage-daemon.log
data_dir: /var/lib/ubuntu-advantage
features:
  extra_security_params:
    hide: true
  new: 2
  show_beta: true
log_file: /var/log/ubuntu-advantage.log
log_level: debug
security_url: https://ubuntu.com/security
settings_overrides:
  c: 1
  d: 2
timer_log_file: /var/log/ubuntu-advantage-timer.log
"""

USER_CFG_DICT = {
    "apt_http_proxy": None,
    "apt_https_proxy": None,
    "apt_news": True,
    "apt_news_url": "https://motd.ubuntu.com/aptnews.json",
    "global_apt_http_proxy": None,
    "global_apt_https_proxy": None,
    "ua_apt_http_proxy": None,
    "ua_apt_https_proxy": None,
    "http_proxy": None,
    "https_proxy": None,
    "update_messaging_timer": 21600,
    "metering_timer": 14400,
}


class TestUserConfigKeys:
    @pytest.mark.parametrize("attr_name", UA_CONFIGURABLE_KEYS)
    @mock.patch("uaclient.config.state_files.user_config_file.write")
    def test_user_configurable_keys_set_user_config(
        self, write, attr_name, tmpdir, FakeConfig
    ):
        """Getters and settings are available fo UA_CONFIGURABLE_KEYS."""
        cfg = FakeConfig()
        assert USER_CFG_DICT[attr_name] == getattr(cfg, attr_name, None)
        cfg_non_members = ("apt_http_proxy", "apt_https_proxy")
        if attr_name not in cfg_non_members:
            setattr(cfg, attr_name, attr_name + "value")
            assert attr_name + "value" == getattr(cfg, attr_name)
            assert attr_name + "value" == getattr(cfg.user_config, attr_name)


class TestWriteCache:
    @pytest.mark.parametrize(
        "key,content",
        (("unknownkey", "content1"), ("another-one", "content2")),
    )
    def test_write_cache_write_key_name_in_data_dir_when_data_path_absent(
        self, tmpdir, FakeConfig, key, content
    ):
        """When key is not in data_paths, write content to data_dir/key."""
        cfg = FakeConfig()
        expected_path = tmpdir.join(PRIVATE_SUBDIR, key)

        assert not expected_path.check(), "Found unexpected file {}".format(
            expected_path
        )
        assert None is cfg.write_cache(key, content)
        assert expected_path.check(), "Missing expected file {}".format(
            expected_path
        )
        assert content == cfg.read_cache(key)

    def test_write_cache_creates_secure_private_dir(self, tmpdir, FakeConfig):
        """private_dir is created with permission 0o700."""
        cfg = FakeConfig()
        # unknown keys are written to the private dir
        expected_dir = tmpdir.join(PRIVATE_SUBDIR)
        assert None is cfg.write_cache("somekey", "somevalue")
        assert True is os.path.isdir(
            expected_dir.strpath
        ), "Missing expected directory {}".format(expected_dir)
        assert 0o700 == stat.S_IMODE(os.lstat(expected_dir.strpath).st_mode)

    def test_write_cache_creates_dir_when_data_dir_does_not_exist(
        self, tmpdir, FakeConfig
    ):
        """When data_dir doesn't exist, create it."""
        tmp_subdir = tmpdir.join("does/not/exist")
        cfg = FakeConfig({"data_dir": tmp_subdir.strpath})

        assert False is os.path.isdir(
            tmp_subdir.strpath
        ), "Found unexpected directory {}".format(tmp_subdir)
        assert None is cfg.write_cache("somekey", "someval")
        assert True is os.path.isdir(
            tmp_subdir.strpath
        ), "Missing expected directory {}".format(tmp_subdir)
        assert "someval" == cfg.read_cache("somekey")

    @pytest.mark.parametrize(
        "key,value", (("dictkey", {"1": "v1"}), ("listkey", [1, 2, 3]))
    )
    def test_write_cache_writes_json_string_when_content_not_a_string(
        self, tmpdir, FakeConfig, key, value
    ):
        """When content is not a string, write a json string."""
        cfg = FakeConfig()

        expected_json_content = json.dumps(value)
        assert None is cfg.write_cache(key, value)
        with open(tmpdir.join(PRIVATE_SUBDIR, key).strpath, "r") as stream:
            assert expected_json_content == stream.read()
        assert value == cfg.read_cache(key)

    @pytest.mark.parametrize(
        "datapath,mode",
        (
            (DataPath("path", False, False), 0o644),
            (DataPath("path", True, False), 0o600),
        ),
    )
    def test_permissions(self, FakeConfig, datapath, mode):
        cfg = FakeConfig()
        cfg.data_paths = {"path": datapath}
        cfg.write_cache("path", "")
        assert mode == stat.S_IMODE(os.lstat(cfg.data_path("path")).st_mode)

    def test_write_datetime(self, FakeConfig):
        cfg = FakeConfig()
        key = "test_key"
        dt = datetime.datetime.now()
        cfg.write_cache(key, dt)
        with open(cfg.data_path(key)) as f:
            assert dt.isoformat() == f.read().strip('"')


class TestReadCache:
    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_read_cache_returns_none_when_data_path_absent(
        self, tmpdir, FakeConfig, key, path_basename
    ):
        """Return None when the specified key data_path is not cached."""
        cfg = FakeConfig()
        assert None is cfg.read_cache(key)
        assert not tmpdir.join(path_basename).check()

    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_read_cache_returns_content_when_data_path_present(
        self, tmpdir, FakeConfig, key, path_basename
    ):
        cfg = FakeConfig()
        os.makedirs(tmpdir.join(PRIVATE_SUBDIR).strpath)
        data_path = tmpdir.join(PRIVATE_SUBDIR, path_basename)
        with open(data_path.strpath, "w") as f:
            f.write("content{}".format(key))

        assert "content{}".format(key) == cfg.read_cache(key)

    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_read_cache_returns_stuctured_content_when_json_data_path_present(
        self, tmpdir, FakeConfig, key, path_basename
    ):
        cfg = FakeConfig()
        os.makedirs(tmpdir.join(PRIVATE_SUBDIR).strpath)
        data_path = tmpdir.join(PRIVATE_SUBDIR, path_basename)
        expected = {key: "content{}".format(key)}
        with open(data_path.strpath, "w") as f:
            f.write(json.dumps(expected))

        assert expected == cfg.read_cache(key)

    def test_datetimes_are_unserialised(self, tmpdir, FakeConfig):
        cfg = FakeConfig()
        os.makedirs(tmpdir.join(PRIVATE_SUBDIR).strpath)
        data_path = tmpdir.join(PRIVATE_SUBDIR, "dt_test")
        with open(data_path.strpath, "w") as f:
            f.write('{"dt": "2019-07-25T14:35:51"}')

        actual = cfg.read_cache("dt_test")
        assert {
            "dt": datetime.datetime(
                2019, 7, 25, 14, 35, 51, tzinfo=datetime.timezone.utc
            )
        } == actual


class TestDeleteCacheKey:
    @pytest.mark.parametrize("property_name", ("status-cache", "lock"))
    def test_delete_cache_key_removes_public_or_private_data_path_files(
        self, property_name, FakeConfig
    ):
        cfg = FakeConfig()
        cfg.write_cache(property_name, "himom")
        assert True is os.path.exists(cfg.data_path(property_name))
        cfg.delete_cache_key(property_name)
        assert False is os.path.exists(cfg.data_path(property_name))
        assert None is cfg.read_cache(property_name)

    @pytest.mark.parametrize(
        "property_name,clears_cache",
        (
            ("machine-token", True),
            ("machine-access-cis", True),
            ("machine", False),
        ),
    )
    def test_delete_cache_key_clears_machine_token_and_entitlements(
        self, property_name, clears_cache, FakeConfig, all_resources_available
    ):
        cfg = FakeConfig()
        token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True},
                        {"type": "entitlement2", "entitled": True},
                    ]
                }
            },
        }
        cfg.machine_token_file.write(token)
        # sets config _entitlements and _machine_token cache
        cfg.machine_token_file.entitlements
        assert cfg.machine_token_file._entitlements is not None
        assert cfg.machine_token_file._machine_token is not None
        if property_name == "machine-token":
            cfg.machine_token_file.delete()
        else:
            cfg.delete_cache_key(property_name)
        if clears_cache:
            # internal cache is cleared
            assert cfg.machine_token_file._entitlements is None
            assert cfg.machine_token_file._machine_token is None

        # Reconstitutes _entitlements and _machine_token caches
        entitlements = cfg.machine_token_file.entitlements
        if property_name == "machine-token":
            # We performed delete_cache_key("machine-token") above, so None now
            assert None is cfg.machine_token_file._entitlements
            assert None is cfg.machine_token
        else:
            # re-constitute from cache
            assert entitlements is cfg.machine_token_file._entitlements
            assert cfg.machine_token_file._machine_token is cfg.machine_token


class TestDeleteCache:
    def test_delete_cache_unsets_entitlements(
        self, FakeConfig, all_resources_available
    ):
        """The delete_cache unsets any cached entitlements content."""
        cfg = FakeConfig()
        token = {
            "availableResources": all_resources_available,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True}
                    ]
                }
            },
        }
        cfg.machine_token_file.write(token)
        previous_entitlements = {
            "entitlement1": {
                "entitlement": {"type": "entitlement1", "entitled": True}
            }
        }
        assert previous_entitlements == cfg.machine_token_file.entitlements
        cfg.delete_cache()
        cfg.machine_token_file.delete()
        assert {} == cfg.machine_token_file.entitlements

    def test_delete_cache_removes_all_data_path_files_with_delete_permanent(
        self, tmpdir, FakeConfig
    ):
        """Any cached files defined in cfg.data_paths will be removed."""
        cfg = FakeConfig()
        # Create half of the cached files, but not all
        odd_keys = list(sorted(cfg.data_paths.keys()))[::2]
        for odd_key in odd_keys:
            if odd_key == "notices":
                # notices key expects specific list or lists format
                value = [[odd_key, odd_key]]
            else:
                value = odd_key
            cfg.write_cache(odd_key, value)

        present_files = list(
            itertools.chain(
                *[walk_entry[2] for walk_entry in os.walk(tmpdir.strpath)]
            )
        )
        assert len(odd_keys) == len(present_files)
        cfg.delete_cache(delete_permanent=True)
        dirty_files = list(
            itertools.chain(
                *[walk_entry[2] for walk_entry in os.walk(tmpdir.strpath)]
            )
        )
        assert 0 == len(dirty_files), "{} files not deleted".format(
            ", ".join(dirty_files)
        )

    def test_delete_cache_ignores_permanent_data_path_files(
        self, tmpdir, FakeConfig
    ):
        """Any cached files defined in cfg.data_paths will be removed."""
        cfg = FakeConfig()
        for key in cfg.data_paths.keys():
            if key == "notices":
                # notices key expects specific list or lists format
                value = [[key, key]]
            else:
                value = key
            cfg.write_cache(key, value)

        num_permanent_files = len(
            [v for v in cfg.data_paths.values() if v.permanent]
        )
        present_files = list(
            itertools.chain(
                *[walk_entry[2] for walk_entry in os.walk(tmpdir.strpath)]
            )
        )
        assert len(cfg.data_paths.keys()) == len(present_files)
        cfg.delete_cache()
        cfg.machine_token_file.delete()
        dirty_files = list(
            itertools.chain(
                *[walk_entry[2] for walk_entry in os.walk(tmpdir.strpath)]
            )
        )
        assert num_permanent_files == len(
            dirty_files
        ), "{} files not deleted".format(", ".join(dirty_files))

    def test_delete_cache_ignores_files_not_defined_in_data_paths(
        self, tmpdir, FakeConfig
    ):
        """Any files in data_dir undefined in cfg.data_paths will remain."""
        cfg = FakeConfig()
        t_file = tmpdir.join(PRIVATE_SUBDIR, "otherfile")
        os.makedirs(os.path.dirname(t_file.strpath))
        with open(t_file.strpath, "w") as f:
            f.write("content")
        assert [os.path.basename(t_file.strpath)] == os.listdir(
            tmpdir.join(PRIVATE_SUBDIR).strpath
        )
        cfg.delete_cache()
        cfg.machine_token_file.delete()
        assert [os.path.basename(t_file.strpath)] == os.listdir(
            tmpdir.join(PRIVATE_SUBDIR).strpath
        )


class TestProcessConfig:
    @pytest.mark.parametrize(
        "http_proxy, https_proxy, snap_is_installed, snap_http_val, "
        "snap_https_val, livepatch_enabled, livepatch_http_val, "
        "livepatch_https_val, snap_livepatch_msg, "
        "global_https, global_http, ua_https, ua_http, apt_https, apt_http",
        [
            (
                "http",
                "https",
                False,
                None,
                None,
                False,
                None,
                None,
                "",
                None,
                None,
                None,
                None,
                None,
                None,
            ),
            (
                "http",
                "https",
                True,
                None,
                None,
                False,
                None,
                None,
                "",
                None,
                None,
                None,
                None,
                "apt_https",
                "apt_http",
            ),
            (
                "http",
                "https",
                False,
                None,
                None,
                True,
                None,
                None,
                "",
                "global_https",
                "global_http",
                None,
                None,
                None,
                None,
            ),
            (
                "http",
                "https",
                True,
                None,
                None,
                True,
                None,
                None,
                "",
                None,
                None,
                "ua_https",
                "ua_http",
                None,
                None,
            ),
            (
                None,
                None,
                True,
                None,
                None,
                True,
                None,
                None,
                "",
                "global_https",
                "global_http",
                None,
                None,
                "apt_https",
                "apt_http",
            ),
            (
                None,
                None,
                True,
                "one",
                None,
                True,
                None,
                None,
                "snap",
                "global_https",
                "global_http",
                "ua_https",
                "ua_http",
                "apt_https",
                "apt_http",
            ),
            (
                None,
                None,
                True,
                "one",
                "two",
                True,
                None,
                None,
                "snap",
                None,
                "global_http",
                None,
                None,
                None,
                "apt_http",
            ),
            (
                None,
                None,
                True,
                "one",
                "two",
                True,
                "three",
                None,
                "snap, livepatch",
                "global_htttps",
                None,
                "ua_https",
                None,
                "apt_https",
                None,
            ),
            (
                None,
                None,
                True,
                "one",
                "two",
                True,
                "three",
                "four",
                "snap, livepatch",
                "global_https",
                None,
                None,
                "ua_http",
                None,
                None,
            ),
            (
                None,
                None,
                False,
                None,
                None,
                True,
                "three",
                "four",
                "livepatch",
                None,
                None,
                None,
                None,
                None,
                None,
            ),
        ],
    )
    @mock.patch("uaclient.util.validate_proxy")
    @mock.patch("uaclient.livepatch.get_config_option_value")
    @mock.patch("uaclient.livepatch.configure_livepatch_proxy")
    @mock.patch(
        "uaclient.entitlements.livepatch.LivepatchEntitlement.application_status"  # noqa: E501
    )
    @mock.patch("uaclient.snap.get_config_option_value")
    @mock.patch("uaclient.snap.configure_snap_proxy")
    @mock.patch("uaclient.snap.is_installed")
    @mock.patch("uaclient.apt.setup_apt_proxy")
    @mock.patch("uaclient.config.state_files.user_config_file.write")
    def test_process_config(
        self,
        m_write,
        m_apt_configure_proxy,
        m_snap_is_installed,
        m_snap_configure_proxy,
        m_snap_get_config_option,
        m_livepatch_status,
        m_livepatch_configure_proxy,
        m_livepatch_get_config_option,
        m_validate_proxy,
        http_proxy,
        https_proxy,
        snap_is_installed,
        snap_http_val,
        snap_https_val,
        livepatch_enabled,
        livepatch_http_val,
        livepatch_https_val,
        snap_livepatch_msg,
        global_https,
        global_http,
        ua_https,
        ua_http,
        apt_https,
        apt_http,
        capsys,
        tmpdir,
        FakeConfig,
    ):
        m_snap_is_installed.return_value = snap_is_installed
        m_snap_get_config_option.side_effect = [snap_http_val, snap_https_val]
        m_livepatch_status.return_value = (
            (ApplicationStatus.ENABLED, None)
            if livepatch_enabled
            else (None, None)
        )
        m_livepatch_get_config_option.side_effect = [
            livepatch_http_val,
            livepatch_https_val,
        ]
        cfg = FakeConfig({"data_dir": tmpdir.strpath})
        cfg.user_config.apt_http_proxy = apt_http
        cfg.user_config.apt_https_proxy = apt_https
        cfg.user_config.global_apt_https_proxy = global_https
        cfg.user_config.global_apt_http_proxy = global_http
        cfg.user_config.ua_apt_https_proxy = ua_https
        cfg.user_config.ua_apt_http_proxy = ua_http
        cfg.user_config.http_proxy = http_proxy
        cfg.user_config.https_proxy = https_proxy
        cfg.user_config.update_messaging_timer = 21600
        cfg.user_config.metering_timer = 0

        if global_https is None and apt_https is not None:
            global_https = apt_https
        if global_http is None and apt_http is not None:
            global_http = apt_http

        exc = False
        if global_https or global_http:
            if ua_https or ua_http:
                exc = True
                with pytest.raises(
                    exceptions.UserFacingError,
                    match=messages.ERROR_PROXY_CONFIGURATION,
                ):
                    cfg.process_config()
        if exc is False:
            cfg.process_config()

            assert [
                mock.call(
                    "http", global_http, util.PROXY_VALIDATION_APT_HTTP_URL
                ),
                mock.call(
                    "https", global_https, util.PROXY_VALIDATION_APT_HTTPS_URL
                ),
                mock.call("http", ua_http, util.PROXY_VALIDATION_APT_HTTP_URL),
                mock.call(
                    "https", ua_https, util.PROXY_VALIDATION_APT_HTTPS_URL
                ),
                mock.call(
                    "http", http_proxy, util.PROXY_VALIDATION_SNAP_HTTP_URL
                ),
                mock.call(
                    "https", https_proxy, util.PROXY_VALIDATION_SNAP_HTTPS_URL
                ),
            ] == m_validate_proxy.call_args_list

            if global_http or global_https:
                assert [
                    mock.call(
                        global_http, global_https, apt.AptProxyScope.GLOBAL
                    )
                ] == m_apt_configure_proxy.call_args_list
            elif ua_http or ua_https:
                assert [
                    mock.call(ua_http, ua_https, apt.AptProxyScope.UACLIENT)
                ] == m_apt_configure_proxy.call_args_list
            else:
                assert [] == m_apt_configure_proxy.call_args_list

            if snap_is_installed:
                assert [
                    mock.call(http_proxy, https_proxy)
                ] == m_snap_configure_proxy.call_args_list

            if livepatch_enabled:
                assert [
                    mock.call(http_proxy, https_proxy)
                ] == m_livepatch_configure_proxy.call_args_list

            expected_out = ""
            if snap_livepatch_msg:
                expected_out = messages.PROXY_DETECTED_BUT_NOT_CONFIGURED.format(  # noqa: E501
                    services=snap_livepatch_msg
                )

            out, err = capsys.readouterr()
            expected_out = """
                Using deprecated "{apt}" config field.
                Please migrate to using "{global_}"
            """
            if apt_http and not global_http:
                assert (
                    expected_out.format(
                        apt=apt_http, global_=global_http
                    ).strip()
                    == out.strip()
                )
            if apt_https and not global_https:
                assert (
                    expected_out.format(
                        apt=apt_https, global_=global_https
                    ).strip()
                    == out.strip()
                )
            assert "" == err

    def test_process_config_errors_for_wrong_timers(self, FakeConfig):
        cfg = FakeConfig()
        cfg.user_config.update_messaging_timer = "wrong"

        with pytest.raises(
            exceptions.UserFacingError,
            match="Value for the update_messaging_timer interval must be "
            "a positive integer. Default value will be used.",
        ):
            cfg.process_config()


class TestParseConfig:
    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    @mock.patch("uaclient.contract.get_available_resources")
    def test_parse_config_uses_defaults_when_no_config_present(
        self, _m_resources, m_exists
    ):
        cwd = os.getcwd()
        with mock.patch.dict("uaclient.config.os.environ", values={}):
            config, _ = parse_config()
        expected_calls = [
            mock.call("{}/uaclient.conf".format(cwd)),
            mock.call("/etc/ubuntu-advantage/uaclient.conf"),
        ]
        assert expected_calls == m_exists.call_args_list
        expected_default_config = {
            "contract_url": "https://contracts.canonical.com",
            "security_url": "https://ubuntu.com/security",
            "data_dir": "/var/lib/ubuntu-advantage",
            "log_file": "/var/log/ubuntu-advantage.log",
            "timer_log_file": "/var/log/ubuntu-advantage-timer.log",
            "daemon_log_file": "/var/log/ubuntu-advantage-daemon.log",  # noqa: E501
            "log_level": "debug",
        }
        assert expected_default_config == config

    @pytest.mark.parametrize(
        "config_dict,expected_invalid_keys",
        (
            ({"contract_url": "http://abc", "security_url": "http:xyz"}, []),
            (
                {"contract_urs": "http://abc", "security_url": "http:xyz"},
                ["contract_urs"],
            ),
        ),
    )
    def test_parse_config_returns_invalid_keys(
        self, config_dict, expected_invalid_keys, tmpdir
    ):
        config_file = tmpdir.join("uaclient.conf")
        config_file.write(yaml.safe_dump(config_dict))
        env_vars = {"UA_CONFIG_FILE": config_file.strpath}
        with mock.patch.dict("uaclient.config.os.environ", values=env_vars):
            cfg, invalid_keys = parse_config(config_file.strpath)
        assert set(expected_invalid_keys) == invalid_keys
        for key, value in config_dict.items():
            if key in VALID_UA_CONFIG_KEYS:
                assert config_dict[key] == cfg[key]

    @pytest.mark.parametrize(
        "envvar_name,envvar_val,field,expected_val",
        [
            # not on allowlist
            (
                "UA_CONTRACT_URL",
                "https://contract",
                "contract_url",
                "https://contracts.canonical.com",
            ),
            # on allowlist
            (
                "UA_security_URL",
                "https://security",
                "security_url",
                "https://security",
            ),
            (
                "ua_data_dir",
                "~/somedir",
                "data_dir",
                "{}/somedir".format(os.path.expanduser("~")),
            ),
            ("Ua_LoG_FiLe", "some.log", "log_file", "some.log"),
            ("UA_LOG_LEVEL", "debug", "log_level", "debug"),
        ],
    )
    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    @mock.patch("uaclient.contract.get_available_resources")
    def test_parse_config_scrubs_user_environ_values(
        self,
        _m_resources,
        m_exists,
        envvar_name,
        envvar_val,
        field,
        expected_val,
    ):
        user_values = {envvar_name: envvar_val}
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            config, _ = parse_config()
        assert expected_val == config[field]

    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_parse_config_scrubs_user_environ_values_features(self, m_exists):
        user_values = {
            "UA_FEATURES_X_Y_Z": "XYZ_VAL",
            "UA_FEATURES_A_B_C": "ABC_VAL",
        }
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            config, _ = parse_config()
        expected_config = {
            "features": {"a_b_c": "ABC_VAL", "x_y_z": "XYZ_VAL"}
        }
        assert expected_config["features"] == config["features"]

    @pytest.mark.parametrize(
        "env_var,env_value", [("UA_SECURITY_URL", "ht://security")]
    )
    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_parse_raises_errors_on_invalid_urls(
        self, _m_exists, env_var, env_value
    ):
        user_values = {env_var: env_value}  # no acceptable url scheme
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            with pytest.raises(exceptions.UserFacingError) as excinfo:
                parse_config()
        expected_msg = "Invalid url in config. {}: {}".format(
            env_var.replace("UA_", "").lower(), env_value
        )
        assert expected_msg == excinfo.value.msg

    @mock.patch("uaclient.config.os.path.exists")
    @mock.patch("uaclient.system.load_file")
    def test_parse_reads_yaml_from_environ_values(
        self, m_load_file, m_path_exists
    ):
        m_load_file.return_value = "test: true\nfoo: bar"
        m_path_exists.side_effect = [False, False, True]

        user_values = {"UA_FEATURES_TEST": "test.yaml"}
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            cfg, _ = parse_config()

        assert {"test": True, "foo": "bar"} == cfg["features"]["test"]

    @mock.patch("uaclient.config.os.path.exists")
    def test_parse_raise_exception_when_environ_yaml_file_does_not_exist(
        self, m_path_exists
    ):
        m_path_exists.return_value = False
        user_values = {"UA_FEATURES_TEST": "test.yaml"}
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            with pytest.raises(exceptions.UserFacingError) as excinfo:
                parse_config()

        expected_msg = "Could not find yaml file: test.yaml"
        assert expected_msg == excinfo.value.msg.strip()


class TestFeatures:
    @pytest.mark.parametrize("caplog_text", [logging.WARNING], indirect=True)
    @pytest.mark.parametrize(
        "cfg_features,expected, warnings",
        (
            ({}, {}, None),
            (None, {}, None),
            (
                "badstring",
                {},
                "Unexpected uaclient.conf features value."
                " Expected dict, but found badstring",
            ),
            ({"feature1": "value1"}, {"feature1": "value1"}, None),
            (
                {"feature1": "value1", "feature2": False},
                {"feature1": "value1", "feature2": False},
                None,
            ),
        ),
    )
    def test_features_are_a_property_of_uaconfig(
        self, cfg_features, expected, warnings, caplog_text, FakeConfig
    ):
        user_cfg = {"features": cfg_features}
        cfg = FakeConfig(cfg_overrides=user_cfg)
        assert expected == cfg.features
        if warnings:
            assert warnings in caplog_text()


class TestMachineTokenOverlay:
    machine_token_dict = {
        "availableResources": [
            {"available": False, "name": "cc-eal"},
            {"available": True, "name": "esm-infra"},
            {"available": False, "name": "fips"},
        ],
        "machineTokenInfo": {
            "contractInfo": {
                "resourceEntitlements": [
                    {
                        "type": "cc-eal",
                        "entitled": False,
                        "affordances": {
                            "architectures": [
                                "amd64",
                                "ppc64el",
                                "ppc64le",
                                "s390x",
                                "x86_64",
                            ],
                            "series": ["xenial"],
                        },
                        "directives": {
                            "additionalPackages": ["ubuntu-commoncriteria"],
                            "aptKey": "key",
                            "aptURL": "https://esm.ubuntu.com/cc",
                            "suites": ["xenial"],
                        },
                    },
                    {
                        "type": "livepatch",
                        "entitled": True,
                        "affordances": {
                            "architectures": ["amd64", "x86_64"],
                            "tier": "stable",
                        },
                        "directives": {
                            "caCerts": "",
                            "remoteServer": "https://livepatch.canonical.com",
                        },
                        "obligations": {"enableByDefault": True},
                    },
                ]
            }
        },
    }

    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.files.MachineTokenFile.read")
    @mock.patch("uaclient.config.os.path.exists", return_value=True)
    def test_machine_token_update_with_overlay(
        self, m_path, m_token_read, m_load_file, FakeConfig
    ):
        user_cfg = {
            "features": {"machine_token_overlay": "machine-token-path"}
        }
        m_token_read.return_value = self.machine_token_dict

        remote_server_overlay = "overlay"
        json_str = json.dumps(
            {
                "availableResources": [
                    {"available": False, "name": "esm-infra"},
                    {"available": True, "name": "test-overlay"},
                ],
                "machineTokenInfo": {
                    "contractInfo": {
                        "resourceEntitlements": [
                            {
                                "type": "livepatch",
                                "entitled": False,
                                "affordances": {"architectures": ["test"]},
                                "directives": {"remoteServer": "overlay"},
                            }
                        ]
                    }
                },
            }
        )
        m_load_file.return_value = json_str

        expected = copy.deepcopy(self.machine_token_dict)
        expected["machineTokenInfo"]["contractInfo"]["resourceEntitlements"][
            1
        ]["directives"]["remoteServer"] = remote_server_overlay
        expected["machineTokenInfo"]["contractInfo"]["resourceEntitlements"][
            1
        ]["affordances"]["architectures"] = ["test"]
        expected["machineTokenInfo"]["contractInfo"]["resourceEntitlements"][
            1
        ]["entitled"] = False
        expected["availableResources"][1]["available"] = False
        expected["availableResources"].append(
            {"available": True, "name": "test-overlay"}
        )

        cfg = FakeConfig(cfg_overrides=user_cfg)
        assert expected == cfg.machine_token

    @mock.patch("uaclient.files.MachineTokenFile.read")
    def test_machine_token_without_overlay(self, m_token_read, FakeConfig):
        user_cfg = {}
        m_token_read.return_value = self.machine_token_dict
        cfg = FakeConfig(cfg_overrides=user_cfg)
        assert self.machine_token_dict == cfg.machine_token

    @mock.patch("uaclient.files.MachineTokenFile.read")
    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_machine_token_overlay_file_not_found(
        self, m_path, m_token_read, FakeConfig
    ):
        invalid_path = "machine-token-path"
        user_cfg = {"features": {"machine_token_overlay": invalid_path}}
        m_token_read.return_value = self.machine_token_dict

        cfg = FakeConfig(cfg_overrides=user_cfg)
        expected_msg = messages.INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY.format(
            file_path=invalid_path
        )

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cfg.machine_token

        assert expected_msg == str(excinfo.value)

    @mock.patch("uaclient.system.load_file")
    @mock.patch("uaclient.files.MachineTokenFile.read")
    @mock.patch("uaclient.config.os.path.exists", return_value=True)
    def test_machine_token_overlay_json_decode_error(
        self, m_path, m_token_read, m_load_file, FakeConfig
    ):
        invalid_json_path = "machine-token-path"
        user_cfg = {"features": {"machine_token_overlay": invalid_json_path}}
        m_token_read.return_value = self.machine_token_dict

        json_str = '{"directives": {"remoteServer": "overlay"}'
        m_load_file.return_value = json_str
        expected_msg = messages.ERROR_JSON_DECODING_IN_FILE.format(
            error="Expecting ',' delimiter: line 1 column 43 (char 42)",
            file_path=invalid_json_path,
        )

        cfg = FakeConfig(cfg_overrides=user_cfg)
        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cfg.machine_token

        assert expected_msg == str(excinfo.value)


class TestDepthFirstMergeOverlayDict:
    @pytest.mark.parametrize(
        "base_dict, overlay_dict, expected_dict",
        [
            ({"a": 1, "b": 2}, {"c": 3}, {"a": 1, "b": 2, "c": 3}),
            (
                {"a": 1, "b": {"c": 2, "d": 3}},
                {"a": 1, "b": {"c": 10}},
                {"a": 1, "b": {"c": 10, "d": 3}},
            ),
            (
                {"a": 1, "b": {"c": 2, "d": 3}},
                {"d": {"f": 20}},
                {"a": 1, "b": {"c": 2, "d": 3}, "d": {"f": 20}},
            ),
            ({"a": 1, "b": 2}, {}, {"a": 1, "b": 2}),
            ({"a": 1, "b": 2}, {"a": "test"}, {"a": "test", "b": 2}),
            ({}, {"a": 1, "b": 2}, {"a": 1, "b": 2}),
            ({"a": []}, {"a": [1, 2, 3]}, {"a": [1, 2, 3]}),
            ({"a": [5, 6]}, {"a": [1, 2, 3]}, {"a": [1, 2, 3]}),
            ({"a": [{"b": 1}]}, {"a": [{"c": 2}]}, {"a": [{"b": 1, "c": 2}]}),
        ],
    )
    def test_depth_first_merge_dict(
        self, base_dict, overlay_dict, expected_dict
    ):
        depth_first_merge_overlay_dict(base_dict, overlay_dict)
        assert expected_dict == base_dict


class TestGetConfigPath:
    def test_get_config_path_from_env_var(self):
        with mock.patch.dict(
            "uaclient.config.os.environ", values={"UA_CONFIG_FILE": "test"}
        ):
            assert "test" == get_config_path()

    @mock.patch("uaclient.config.os.path.join", return_value="test123")
    @mock.patch("uaclient.config.os.path.exists", return_value=True)
    def test_get_config_path_from_local_dir(self, _m_exists, _m_join):
        with mock.patch.dict("uaclient.config.os.environ", values={}):
            assert "test123" == get_config_path()
            assert _m_join.call_count == 1
            assert _m_exists.call_count == 1

    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_get_default_config_path(self, _m_exists):
        with mock.patch.dict("uaclient.config.os.environ", values={}):
            assert DEFAULT_CONFIG_FILE == get_config_path()
            assert _m_exists.call_count == 1


class TestCheckLockInfo:
    @pytest.mark.parametrize("lock_content", ((""), ("corrupted")))
    @mock.patch("os.path.exists", return_value=True)
    @mock.patch("uaclient.system.load_file")
    def test_raise_exception_for_corrupted_lock(
        self,
        m_load_file,
        _m_path_exists,
        lock_content,
        FakeConfig,
    ):
        cfg = FakeConfig()
        m_load_file.return_value = lock_content

        expected_msg = messages.INVALID_LOCK_FILE.format(
            lock_file_path=cfg.data_dir + "/lock"
        )

        with pytest.raises(exceptions.InvalidLockFile) as exc_info:
            cfg.check_lock_info()

        assert expected_msg.msg == exc_info.value.msg
        assert m_load_file.call_count == 1
        assert _m_path_exists.call_count == 1

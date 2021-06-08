import copy
import datetime
import itertools
import json
import logging
import os
import stat

import mock
import pytest

from uaclient import entitlements, exceptions, status
from uaclient.config import (
    DataPath,
    DEFAULT_STATUS,
    PRIVATE_SUBDIR,
    UAConfig,
    parse_config,
    depth_first_merge_overlay_dict,
)
from uaclient.entitlements import (
    ENTITLEMENT_CLASSES,
    ENTITLEMENT_CLASS_BY_NAME,
)
from uaclient.status import (
    ContractStatus,
    UserFacingStatus,
    UserFacingConfigStatus,
    MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL,
)


KNOWN_DATA_PATHS = (
    ("machine-access-cis", "machine-access-cis.json"),
    ("machine-token", "machine-token.json"),
)
M_PATH = "uaclient.entitlements."

DEFAULT_CFG_STATUS = {
    "configStatus": DEFAULT_STATUS["configStatus"],
    "configStatusDetails": DEFAULT_STATUS["configStatusDetails"],
}

ALL_RESOURCES_AVAILABLE = [
    {"name": name, "available": True} for name in ENTITLEMENT_CLASS_BY_NAME
]
ALL_RESOURCES_ENTITLED = [
    {"type": name, "entitled": True} for name in ENTITLEMENT_CLASS_BY_NAME
]
NO_RESOURCES_ENTITLED = [
    {"type": name, "entitled": False} for name in ENTITLEMENT_CLASS_BY_NAME
]
RESP_ONLY_FIPS_RESOURCE_AVAILABLE = [
    {"name": name, "available": name == "fips"}
    for name in ENTITLEMENT_CLASS_BY_NAME
]


class TestNotices:
    @pytest.mark.parametrize(
        "notices,expected",
        (
            ([], []),
            ([["a", "a1"]], [["a", "a1"]]),
            ([["a", "a1"], ["a", "a1"]], [["a", "a1"]]),
        ),
    )
    def test_add_notice_avoids_duplicates(self, notices, expected, tmpdir):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        assert None is cfg.read_cache("notices")
        for notice in notices:
            cfg.add_notice(*notice)
        if notices:
            assert expected == cfg.read_cache("notices")
        else:
            assert None is cfg.read_cache("notices")

    @pytest.mark.parametrize(
        "notices,removes,expected",
        (
            ([], [["a", "a1"]], None),
            ([["a", "a1"]], [["a", "a1"]], None),
            ([["a", "a1"], ["a", "a2"]], [["a", "a1"]], [["a", "a2"]]),
            (
                [["a", "a1"], ["a", "a2"], ["b", "b2"]],
                [["a", ".*"]],
                [["b", "b2"]],
            ),
        ),
    )
    def test_remove_notice_removes_matching(
        self, notices, removes, expected, tmpdir
    ):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        for notice in notices:
            cfg.add_notice(*notice)
        for label, descr in removes:
            cfg.remove_notice(label, descr)
        assert expected == cfg.read_cache("notices")


class TestEntitlements:
    def test_entitlements_property_keyed_by_entitlement_name(self, tmpdir):
        """Return machine_token resourceEntitlements, keyed by name."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        token = {
            "availableResources": ALL_RESOURCES_AVAILABLE,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True},
                        {"type": "entitlement2", "entitled": True},
                    ]
                }
            },
        }
        cfg.write_cache("machine-token", token)
        expected = {
            "entitlement1": {
                "entitlement": {"entitled": True, "type": "entitlement1"}
            },
            "entitlement2": {
                "entitlement": {"entitled": True, "type": "entitlement2"}
            },
        }
        assert expected == cfg.entitlements

    def test_entitlements_uses_resource_token_from_machine_token(self, tmpdir):
        """Include entitlement-specicific resourceTokens from machine_token"""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        token = {
            "availableResources": ALL_RESOURCES_AVAILABLE,
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
        cfg.write_cache("machine-token", token)
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
        assert expected == cfg.entitlements


class TestAccounts:
    def test_accounts_returns_empty_list_when_no_cached_account_value(
        self, tmpdir
    ):
        """Config.accounts property returns an empty list when no cache."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})

        assert [] == cfg.accounts

    def test_accounts_extracts_accounts_key_from_machine_token_cache(
        self, tmpdir
    ):
        """Use machine_token cached accountInfo when no accounts cache."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        accountInfo = {"id": "1", "name": "accountname"}

        cfg.write_cache(
            "machine-token",
            {
                "availableResources": ALL_RESOURCES_AVAILABLE,
                "machineTokenInfo": {"accountInfo": accountInfo},
            },
        )

        assert [accountInfo] == cfg.accounts


class TestDataPath:
    def test_data_path_returns_data_dir_path_without_key(self):
        """The data_path method returns the data_dir when key is absent."""
        cfg = UAConfig({"data_dir": "/my/dir"})
        assert "/my/dir/{}".format(PRIVATE_SUBDIR) == cfg.data_path()

    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_data_path_returns_file_path_with_defined_data_paths(
        self, key, path_basename
    ):
        """When key is defined in Config.data_paths return data_path value."""
        cfg = UAConfig({"data_dir": "/my/dir"})
        private_path = "/my/dir/{}/{}".format(PRIVATE_SUBDIR, path_basename)
        assert private_path == cfg.data_path(key=key)

    @pytest.mark.parametrize(
        "key,path_basename", (("notHere", "notHere"), ("anything", "anything"))
    )
    def test_data_path_returns_file_path_with_undefined_data_paths(
        self, key, path_basename
    ):
        """When key is not in Config.data_paths the key is used to data_dir"""
        cfg = UAConfig({"data_dir": "/my/d"})
        assert "/my/d/{}/{}".format(PRIVATE_SUBDIR, key) == cfg.data_path(
            key=key
        )

    def test_data_path_returns_public_path_for_public_datapath(self):
        cfg = UAConfig({"data_dir": "/my/d"})
        cfg.data_paths["test_path"] = DataPath("test_path", False)
        assert "/my/d/test_path" == cfg.data_path("test_path")


class TestWriteCache:
    @pytest.mark.parametrize(
        "key,clears_cache",
        (
            ("machine-token", True),
            ("machine-access-cis", True),
            ("lock", False),
        ),
    )
    def test_write_cache_clears_machine_token_and_entitlements_instance_vars(
        self, key, clears_cache, tmpdir
    ):
        """Clear _machine_token and _entitlements when machine keys updated."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        # setup cached values
        cfg._machine_token = mock.sentinel.token
        cfg._entitlements = mock.sentinel.entitlements
        cfg.write_cache(key, "something")
        if clears_cache:
            assert None is cfg._entitlements
            assert None is cfg._machine_token
        else:
            assert mock.sentinel.token is cfg._machine_token
            assert mock.sentinel.entitlements is cfg._entitlements

    @pytest.mark.parametrize(
        "key,content",
        (("unknownkey", "content1"), ("another-one", "content2")),
    )
    def test_write_cache_write_key_name_in_data_dir_when_data_path_absent(
        self, tmpdir, key, content
    ):
        """When key is not in data_paths, write content to data_dir/key."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        expected_path = tmpdir.join(PRIVATE_SUBDIR, key)

        assert not expected_path.check(), "Found unexpected file {}".format(
            expected_path
        )
        assert None is cfg.write_cache(key, content)
        assert expected_path.check(), "Missing expected file {}".format(
            expected_path
        )
        assert content == cfg.read_cache(key)

    def test_write_cache_creates_secure_private_dir(self, tmpdir):
        """private_dir is created with permission 0o700."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        # unknown keys are written to the private dir
        expected_dir = tmpdir.join(PRIVATE_SUBDIR)
        assert None is cfg.write_cache("somekey", "somevalue")
        assert True is os.path.isdir(
            expected_dir.strpath
        ), "Missing expected directory {}".format(expected_dir)
        assert 0o700 == stat.S_IMODE(os.lstat(expected_dir.strpath).st_mode)

    def test_write_cache_creates_dir_when_data_dir_does_not_exist(
        self, tmpdir
    ):
        """When data_dir doesn't exist, create it."""
        tmp_subdir = tmpdir.join("does/not/exist")
        cfg = UAConfig({"data_dir": tmp_subdir.strpath})

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
        self, tmpdir, key, value
    ):
        """When content is not a string, write a json string."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})

        expected_json_content = json.dumps(value)
        assert None is cfg.write_cache(key, value)
        with open(tmpdir.join(PRIVATE_SUBDIR, key).strpath, "r") as stream:
            assert expected_json_content == stream.read()
        assert value == cfg.read_cache(key)

    @pytest.mark.parametrize(
        "datapath,mode",
        ((DataPath("path", False), 0o644), (DataPath("path", True), 0o600)),
    )
    def test_permissions(self, tmpdir, datapath, mode):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        cfg.data_paths = {"path": datapath}
        cfg.write_cache("path", "")
        assert mode == stat.S_IMODE(os.lstat(cfg.data_path("path")).st_mode)

    def test_write_datetime(self, tmpdir):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        key = "test_key"
        dt = datetime.datetime.now()
        cfg.write_cache(key, dt)
        with open(cfg.data_path(key)) as f:
            assert dt.isoformat() == f.read().strip('"')


class TestReadCache:
    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_read_cache_returns_none_when_data_path_absent(
        self, tmpdir, key, path_basename
    ):
        """Return None when the specified key data_path is not cached."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        assert None is cfg.read_cache(key)
        assert not tmpdir.join(path_basename).check()

    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_read_cache_returns_content_when_data_path_present(
        self, tmpdir, key, path_basename
    ):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        os.makedirs(tmpdir.join(PRIVATE_SUBDIR).strpath)
        data_path = tmpdir.join(PRIVATE_SUBDIR, path_basename)
        with open(data_path.strpath, "w") as f:
            f.write("content{}".format(key))

        assert "content{}".format(key) == cfg.read_cache(key)

    @pytest.mark.parametrize("key,path_basename", KNOWN_DATA_PATHS)
    def test_read_cache_returns_stuctured_content_when_json_data_path_present(
        self, tmpdir, key, path_basename
    ):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        os.makedirs(tmpdir.join(PRIVATE_SUBDIR).strpath)
        data_path = tmpdir.join(PRIVATE_SUBDIR, path_basename)
        expected = {key: "content{}".format(key)}
        with open(data_path.strpath, "w") as f:
            f.write(json.dumps(expected))

        assert expected == cfg.read_cache(key)

    def test_datetimes_are_unserialised(self, tmpdir):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
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
        self, property_name, tmpdir
    ):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
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
        self, property_name, clears_cache, tmpdir
    ):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        token = {
            "availableResources": ALL_RESOURCES_AVAILABLE,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True},
                        {"type": "entitlement2", "entitled": True},
                    ]
                }
            },
        }
        cfg.write_cache("machine-token", token)
        cfg.entitlements  # sets config _entitlements and _machine_token cache
        assert cfg._entitlements is not None
        assert cfg._machine_token is not None
        cfg.delete_cache_key(property_name)
        if clears_cache:
            # internal cache is cleared
            assert cfg._entitlements is None
            assert cfg._machine_token is None

        # Reconstitutes _entitlements and _machine_token caches
        entitlements = cfg.entitlements
        if property_name == "machine-token":
            # We performed delete_cache_key("machine-token") above, so None now
            assert None is cfg._entitlements
            assert None is cfg.machine_token
        else:
            # re-constitute from cache
            assert entitlements is cfg._entitlements
            assert cfg._machine_token is cfg.machine_token


class TestDeleteCache:
    @pytest.mark.parametrize(
        "property_name,data_path_name,expected_null_value",
        (("machine_token", "machine-token", None),),
    )
    def test_delete_cache_properly_clears_all_caches_simple(
        self, tmpdir, property_name, data_path_name, expected_null_value
    ):
        """
        Ensure that delete_cache clears the cache for simple attributes

        (Simple in this context means those that are simply read from the
        filesystem and returned.)
        """
        property_value = "our-value"
        cfg = UAConfig({"data_dir": tmpdir.strpath})

        data_path = cfg.data_path(data_path_name)
        os.makedirs(os.path.dirname(data_path))
        with open(data_path, "w") as f:
            f.write(property_value)

        before_prop_value = getattr(cfg, property_name)
        assert before_prop_value == property_value

        cfg.delete_cache()

        after_prop_value = getattr(cfg, property_name)
        assert expected_null_value == after_prop_value

    def test_delete_cache_unsets_entitlements(self, tmpdir):
        """The delete_cache unsets any cached entitlements content."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        token = {
            "availableResources": ALL_RESOURCES_AVAILABLE,
            "machineTokenInfo": {
                "contractInfo": {
                    "resourceEntitlements": [
                        {"type": "entitlement1", "entitled": True}
                    ]
                }
            },
        }
        cfg.write_cache("machine-token", token)
        previous_entitlements = {
            "entitlement1": {
                "entitlement": {"type": "entitlement1", "entitled": True}
            }
        }
        assert previous_entitlements == cfg.entitlements
        cfg.delete_cache()
        assert {} == cfg.entitlements

    def test_delete_cache_removes_any_cached_data_path_files(self, tmpdir):
        """Any cached files defined in cfg.data_paths will be removed."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
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
        cfg.delete_cache()
        dirty_files = list(
            itertools.chain(
                *[walk_entry[2] for walk_entry in os.walk(tmpdir.strpath)]
            )
        )
        assert 0 == len(dirty_files), "{} files not deleted".format(
            ", ".join(dirty_files)
        )

    def test_delete_cache_ignores_files_not_defined_in_data_paths(
        self, tmpdir
    ):
        """Any files in data_dir undefined in cfg.data_paths will remain."""
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        t_file = tmpdir.join(PRIVATE_SUBDIR, "otherfile")
        os.makedirs(os.path.dirname(t_file.strpath))
        with open(t_file.strpath, "w") as f:
            f.write("content")
        assert [os.path.basename(t_file.strpath)] == os.listdir(
            tmpdir.join(PRIVATE_SUBDIR).strpath
        )
        cfg.delete_cache()
        assert [os.path.basename(t_file.strpath)] == os.listdir(
            tmpdir.join(PRIVATE_SUBDIR).strpath
        )


@mock.patch("uaclient.config.UAConfig.remove_notice")
@mock.patch("uaclient.util.should_reboot", return_value=False)
class TestStatus:
    esm_desc = ENTITLEMENT_CLASS_BY_NAME["esm-infra"].description
    cc_eal_desc = ENTITLEMENT_CLASS_BY_NAME["cc-eal"].description

    def check_beta(self, cls, show_beta, uacfg=None, status=""):
        if not show_beta:
            if status == "enabled":
                return False

            if uacfg:
                allow_beta = uacfg.cfg.get("features", {}).get(
                    "allow_beta", False
                )

                if allow_beta:
                    return False

            return cls.is_beta

        return False

    @pytest.mark.parametrize(
        "show_beta,expected_services",
        (
            (
                True,
                [
                    {
                        "available": "no",
                        "name": "cc-eal",
                        "description": cc_eal_desc,
                    },
                    {
                        "available": "yes",
                        "name": "esm-infra",
                        "description": esm_desc,
                    },
                ],
            ),
            (
                False,
                [
                    {
                        "available": "yes",
                        "name": "esm-infra",
                        "description": esm_desc,
                    }
                ],
            ),
        ),
    )
    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch("uaclient.config.os.getuid", return_value=0)
    def test_root_unattached(
        self,
        _m_getuid,
        m_get_available_resources,
        _m_should_reboot,
        m_remove_notice,
        show_beta,
        expected_services,
        FakeConfig,
    ):
        """Test we get the correct status dict when unattached"""
        cfg = FakeConfig()
        m_get_available_resources.return_value = [
            {"name": "esm-infra", "available": True},
            {"name": "cc-eal", "available": False},
        ]
        expected = copy.deepcopy(DEFAULT_STATUS)
        expected["services"] = expected_services
        with mock.patch(
            "uaclient.config.UAConfig._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            assert expected == cfg.status(show_beta=show_beta)

            expected_calls = [
                mock.call(
                    "",
                    status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                        operation="fix operation"
                    ),
                )
            ]

            assert expected_calls == m_remove_notice.call_args_list

    @pytest.mark.parametrize("show_beta", (True, False))
    @pytest.mark.parametrize(
        "features_override", ((None), ({"allow_beta": True}))
    )
    @pytest.mark.parametrize(
        "avail_res,entitled_res,uf_entitled,uf_status",
        (
            (  # Empty lists means UNENTITLED and UNAVAILABLE
                [],
                [],
                status.ContractStatus.UNENTITLED.value,
                status.UserFacingStatus.UNAVAILABLE.value,
            ),
            (  # available == False means UNAVAILABLE
                [{"name": "livepatch", "available": False}],
                [],
                status.ContractStatus.UNENTITLED.value,
                status.UserFacingStatus.UNAVAILABLE.value,
            ),
            (  # available == True but unentitled means UNAVAILABLE
                [{"name": "livepatch", "available": True}],
                [],
                status.ContractStatus.UNENTITLED.value,
                status.UserFacingStatus.UNAVAILABLE.value,
            ),
            (  # available == False and entitled means INAPPLICABLE
                [{"name": "livepatch", "available": False}],
                [{"type": "livepatch", "entitled": True}],
                status.ContractStatus.ENTITLED.value,
                status.UserFacingStatus.INAPPLICABLE.value,
            ),
        ),
    )
    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch("uaclient.config.os.getuid", return_value=0)
    def test_root_attached(
        self,
        _m_getuid,
        m_get_avail_resources,
        _m_should_reboot,
        _m_remove_notice,
        avail_res,
        entitled_res,
        uf_entitled,
        uf_status,
        features_override,
        show_beta,
        FakeConfig,
    ):
        """Test we get the correct status dict when attached with basic conf"""
        resource_names = [resource["name"] for resource in avail_res]
        default_entitled = status.ContractStatus.UNENTITLED.value
        default_status = status.UserFacingStatus.UNAVAILABLE.value
        token = {
            "availableResources": [],
            "machineTokenInfo": {
                "accountInfo": {"id": "acct-1", "name": "test_account"},
                "contractInfo": {
                    "id": "cid",
                    "name": "test_contract",
                    "resourceEntitlements": entitled_res,
                },
            },
        }

        available_resource_response = [
            {
                "name": cls.name,
                "available": bool(
                    {"name": cls.name, "available": True} in avail_res
                ),
            }
            for cls in entitlements.ENTITLEMENT_CLASSES
        ]
        if avail_res:
            token["availableResources"] = available_resource_response
        else:
            m_get_avail_resources.return_value = available_resource_response

        cfg = FakeConfig.for_attached_machine(machine_token=token)
        if features_override:
            cfg.override_features(features_override)

        expected_services = [
            {
                "description": cls.description,
                "entitled": uf_entitled
                if cls.name in resource_names
                else default_entitled,
                "name": cls.name,
                "status": uf_status
                if cls.name in resource_names
                else default_status,
                "statusDetails": mock.ANY,
                "description_override": None,
            }
            for cls in entitlements.ENTITLEMENT_CLASSES
            if not self.check_beta(cls, show_beta, cfg)
        ]
        expected = copy.deepcopy(DEFAULT_STATUS)
        expected.update(
            {
                "account-id": "acct-1",
                "account": "test_account",
                "attached": True,
                "services": expected_services,
                "subscription": "test_contract",
                "subscription-id": "cid",
            }
        )
        with mock.patch(
            "uaclient.config.UAConfig._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            assert expected == cfg.status(show_beta=show_beta)
        if avail_res:
            assert m_get_avail_resources.call_count == 0
        else:
            assert m_get_avail_resources.call_count == 1
        # cfg.status() idempotent
        with mock.patch(
            "uaclient.config.UAConfig._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            assert expected == cfg.status(show_beta=show_beta)

    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch("uaclient.config.os.getuid")
    def test_nonroot_unattached_is_same_as_unattached_root(
        self,
        m_getuid,
        m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        FakeConfig,
    ):
        m_get_available_resources.return_value = [
            {"name": "esm-infra", "available": True}
        ]
        m_getuid.return_value = 1000
        cfg = FakeConfig()
        nonroot_status = cfg.status()

        m_getuid.return_value = 0
        root_unattached_status = cfg.status()

        assert root_unattached_status == nonroot_status

    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch("uaclient.config.os.getuid")
    def test_root_followed_by_nonroot(
        self,
        m_getuid,
        m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        tmpdir,
        FakeConfig,
    ):
        """Ensure that non-root run after root returns data"""
        cfg = UAConfig({"data_dir": tmpdir.strpath})

        # Run as root
        m_getuid.return_value = 0
        before = copy.deepcopy(cfg.status())

        # Replicate an attach by modifying the underlying config and confirm
        # that we see different status
        other_cfg = FakeConfig.for_attached_machine()
        cfg.write_cache("accounts", {"accounts": other_cfg.accounts})
        cfg.write_cache("machine-token", other_cfg.machine_token)
        assert cfg._attached_status() != before

        # Run as regular user and confirm that we see the result from
        # last time we called .status()
        m_getuid.return_value = 1000
        after = cfg.status()

        assert before == after

    @mock.patch("uaclient.contract.get_available_resources", return_value=[])
    @mock.patch("uaclient.config.os.getuid", return_value=0)
    def test_cache_file_is_written_world_readable(
        self,
        _m_getuid,
        _m_get_available_resources,
        _m_should_reboot,
        m_remove_notice,
        tmpdir,
    ):
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        cfg.status()

        assert 0o644 == stat.S_IMODE(
            os.lstat(cfg.data_path("status-cache")).st_mode
        )

        expected_calls = [
            mock.call(
                "",
                status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                    operation="fix operation"
                ),
            )
        ]

        assert expected_calls == m_remove_notice.call_args_list

    @pytest.mark.parametrize("show_beta", (True, False))
    @pytest.mark.parametrize(
        "features_override", ((None), ({"allow_beta": False}))
    )
    @pytest.mark.parametrize(
        "entitlements",
        (
            [],
            [
                {
                    "type": "support",
                    "entitled": True,
                    "affordances": {"supportLevel": "anything"},
                }
            ],
        ),
    )
    @mock.patch("uaclient.config.os.getuid", return_value=0)
    @mock.patch(M_PATH + "livepatch.LivepatchEntitlement.user_facing_status")
    @mock.patch(M_PATH + "livepatch.LivepatchEntitlement.contract_status")
    @mock.patch(M_PATH + "esm.ESMAppsEntitlement.user_facing_status")
    @mock.patch(M_PATH + "esm.ESMAppsEntitlement.contract_status")
    @mock.patch(M_PATH + "repo.RepoEntitlement.user_facing_status")
    @mock.patch(M_PATH + "repo.RepoEntitlement.contract_status")
    def test_attached_reports_contract_and_service_status(
        self,
        m_repo_contract_status,
        m_repo_uf_status,
        m_esm_contract_status,
        m_esm_uf_status,
        m_livepatch_contract_status,
        m_livepatch_uf_status,
        _m_getuid,
        _m_should_reboot,
        m_remove_notice,
        entitlements,
        features_override,
        show_beta,
        FakeConfig,
    ):
        """When attached, return contract and service user-facing status."""
        m_repo_contract_status.return_value = status.ContractStatus.ENTITLED
        m_repo_uf_status.return_value = (
            status.UserFacingStatus.INAPPLICABLE,
            "repo details",
        )
        m_livepatch_contract_status.return_value = (
            status.ContractStatus.ENTITLED
        )
        m_livepatch_uf_status.return_value = (
            status.UserFacingStatus.ACTIVE,
            "livepatch details",
        )
        m_esm_contract_status.return_value = status.ContractStatus.ENTITLED
        m_esm_uf_status.return_value = (
            status.UserFacingStatus.ACTIVE,
            "esm-apps details",
        )
        token = {
            "availableResources": ALL_RESOURCES_AVAILABLE,
            "machineTokenInfo": {
                "accountInfo": {"id": "1", "name": "accountname"},
                "contractInfo": {
                    "id": "contract-1",
                    "name": "contractname",
                    "resourceEntitlements": entitlements,
                },
            },
        }
        cfg = FakeConfig.for_attached_machine(
            account_name="accountname", machine_token=token
        )
        if features_override:
            cfg.override_features(features_override)
        if not entitlements:
            support_level = status.UserFacingStatus.INAPPLICABLE.value
        else:
            support_level = entitlements[0]["affordances"]["supportLevel"]
        expected = copy.deepcopy(DEFAULT_STATUS)
        expected.update(
            {
                "attached": True,
                "account": "accountname",
                "account-id": "1",
                "subscription": "contractname",
                "subscription-id": "contract-1",
                "techSupportLevel": support_level,
            }
        )
        for cls in ENTITLEMENT_CLASSES:
            if cls.name == "livepatch":
                expected_status = status.UserFacingStatus.ACTIVE.value
                details = "livepatch details"
            elif cls.name == "esm-apps":
                expected_status = status.UserFacingStatus.ACTIVE.value
                details = "esm-apps details"
            else:
                expected_status = status.UserFacingStatus.INAPPLICABLE.value
                details = "repo details"

            if self.check_beta(cls, show_beta, cfg, expected_status):
                continue

            expected["services"].append(
                {
                    "name": cls.name,
                    "description": cls.description,
                    "entitled": status.ContractStatus.ENTITLED.value,
                    "status": expected_status,
                    "statusDetails": details,
                    "description_override": None,
                }
            )
        with mock.patch(
            "uaclient.config.UAConfig._get_config_status"
        ) as m_get_cfg_status:
            m_get_cfg_status.return_value = DEFAULT_CFG_STATUS
            assert expected == cfg.status(show_beta=show_beta)

        assert len(ENTITLEMENT_CLASSES) - 2 == m_repo_uf_status.call_count
        assert 1 == m_livepatch_uf_status.call_count

        expected_calls = [
            mock.call(
                "",
                status.MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
                    operation="fix operation"
                ),
            )
        ]

        assert expected_calls == m_remove_notice.call_args_list

    @mock.patch("uaclient.contract.get_available_resources")
    @mock.patch("uaclient.config.os.getuid")
    def test_expires_handled_appropriately(
        self,
        m_getuid,
        _m_get_available_resources,
        _m_should_reboot,
        _m_remove_notice,
        FakeConfig,
    ):
        token = {
            "availableResources": ALL_RESOURCES_AVAILABLE,
            "machineTokenInfo": {
                "accountInfo": {"id": "1", "name": "accountname"},
                "contractInfo": {
                    "name": "contractname",
                    "id": "contract-1",
                    "effectiveTo": "2020-07-18T00:00:00Z",
                    "resourceEntitlements": [],
                },
            },
        }
        cfg = FakeConfig.for_attached_machine(
            account_name="accountname", machine_token=token
        )

        # Test that root's status works as expected (including the cache write)
        m_getuid.return_value = 0
        expected_dt = datetime.datetime(
            2020, 7, 18, 0, 0, 0, tzinfo=datetime.timezone.utc
        )
        assert expected_dt == cfg.status()["expires"]

        # Test that the read from the status cache work properly for non-root
        # users
        m_getuid.return_value = 1000
        assert expected_dt == cfg.status()["expires"]

    @mock.patch("uaclient.config.os.getuid")
    def test_nonroot_user_uses_cache_and_updates_if_available(
        self, m_getuid, _m_should_reboot, m_remove_notice, tmpdir
    ):
        m_getuid.return_value = 1000

        expected_status = {"pass": True}
        cfg = UAConfig({"data_dir": tmpdir.strpath})
        cfg.write_cache("marker-reboot-cmds", "")  # To indicate a reboot reqd
        cfg.write_cache("status-cache", expected_status)

        # Even non-root users can update configStatus details
        details = MESSAGE_ENABLE_REBOOT_REQUIRED_TMPL.format(
            operation="configuration changes"
        )
        expected_status.update(
            {
                "configStatus": UserFacingConfigStatus.REBOOTREQUIRED.value,
                "configStatusDetails": details,
                "notices": [],
            }
        )

        assert expected_status == cfg.status()


ATTACHED_SERVICE_STATUS_PARAMETERS = [
    # ENTITLED => display the given user-facing status
    (ContractStatus.ENTITLED, UserFacingStatus.ACTIVE, False, "enabled"),
    (ContractStatus.ENTITLED, UserFacingStatus.INACTIVE, False, "disabled"),
    (ContractStatus.ENTITLED, UserFacingStatus.INAPPLICABLE, False, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.UNAVAILABLE, False, "—"),
    # UNENTITLED => UNAVAILABLE
    (ContractStatus.UNENTITLED, UserFacingStatus.ACTIVE, False, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INACTIVE, False, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INAPPLICABLE, False, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.UNAVAILABLE, [], "—"),
    # ENTITLED but in unavailable_resources => INAPPLICABLE
    (ContractStatus.ENTITLED, UserFacingStatus.ACTIVE, True, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.INACTIVE, True, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.INAPPLICABLE, True, "n/a"),
    (ContractStatus.ENTITLED, UserFacingStatus.UNAVAILABLE, True, "n/a"),
    # UNENTITLED and in unavailable_resources => UNAVAILABLE
    (ContractStatus.UNENTITLED, UserFacingStatus.ACTIVE, True, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INACTIVE, True, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.INAPPLICABLE, True, "—"),
    (ContractStatus.UNENTITLED, UserFacingStatus.UNAVAILABLE, True, "—"),
]


class TestAttachedServiceStatus:
    @pytest.mark.parametrize(
        "contract_status,uf_status,in_inapplicable_resources,expected_status",
        ATTACHED_SERVICE_STATUS_PARAMETERS,
    )
    def test_status(
        self,
        contract_status,
        uf_status,
        in_inapplicable_resources,
        expected_status,
        FakeConfig,
    ):
        ent = mock.MagicMock()
        ent.name = "test_entitlement"
        ent.contract_status.return_value = contract_status
        ent.user_facing_status.return_value = (uf_status, "")

        unavailable_resources = (
            {ent.name: ""} if in_inapplicable_resources else {}
        )
        ret = FakeConfig()._attached_service_status(ent, unavailable_resources)

        assert expected_status == ret["status"]


class TestParseConfig:
    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_parse_config_uses_defaults_when_no_config_present(self, m_exists):
        cwd = os.getcwd()
        with mock.patch.dict("uaclient.config.os.environ", values={}):
            config = parse_config()
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
            "log_level": "INFO",
        }
        assert expected_default_config == config

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
            ("UA_LOG_LEVEL", "debug", "log_level", "DEBUG"),
        ],
    )
    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_parse_config_scrubs_user_environ_values(
        self, m_exists, envvar_name, envvar_val, field, expected_val
    ):
        user_values = {envvar_name: envvar_val}
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            config = parse_config()
        assert expected_val == config[field]

    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_parse_config_scrubs_user_environ_values_features(self, m_exists):
        user_values = {
            "UA_FEATURES_X_Y_Z": "XYZ_VAL",
            "UA_FEATURES_A_B_C": "ABC_VAL",
        }
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            config = parse_config()
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
    @mock.patch("uaclient.util.load_file")
    def test_parse_reads_yaml_from_environ_values(
        self, m_load_file, m_path_exists
    ):
        m_load_file.return_value = "test: true\nfoo: bar"
        m_path_exists.side_effect = [False, False, True]

        user_values = {"UA_FEATURES_TEST": "test.yaml"}
        with mock.patch.dict("uaclient.config.os.environ", values=user_values):
            cfg = parse_config()

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
        self, cfg_features, expected, warnings, caplog_text
    ):
        user_cfg = {"features": cfg_features}
        cfg = UAConfig(cfg=user_cfg)
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

    @mock.patch("uaclient.util.load_file")
    @mock.patch("uaclient.config.UAConfig.read_cache")
    @mock.patch("uaclient.config.os.path.exists", return_value=True)
    def test_machine_token_update_with_overlay(
        self, m_path, m_read_cache, m_load_file
    ):
        user_cfg = {
            "features": {"machine_token_overlay": "machine-token-path"}
        }
        m_read_cache.return_value = self.machine_token_dict

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

        cfg = UAConfig(cfg=user_cfg)
        print(expected)
        print(cfg.machine_token)
        assert expected == cfg.machine_token

    @mock.patch("uaclient.config.UAConfig.read_cache")
    def test_machine_token_without_overlay(self, m_read_cache):
        user_cfg = {}
        m_read_cache.return_value = self.machine_token_dict
        cfg = UAConfig(cfg=user_cfg)
        assert self.machine_token_dict == cfg.machine_token

    @mock.patch("uaclient.config.UAConfig.read_cache")
    @mock.patch("uaclient.config.os.path.exists", return_value=False)
    def test_machine_token_overlay_file_not_found(self, m_path, m_read_cache):
        invalid_path = "machine-token-path"
        user_cfg = {"features": {"machine_token_overlay": invalid_path}}
        m_read_cache.return_value = self.machine_token_dict

        cfg = UAConfig(cfg=user_cfg)
        expected_msg = status.INVALID_PATH_FOR_MACHINE_TOKEN_OVERLAY.format(
            file_path=invalid_path
        )

        with pytest.raises(exceptions.UserFacingError) as excinfo:
            cfg.machine_token

        assert expected_msg == str(excinfo.value)

    @mock.patch("uaclient.util.load_file")
    @mock.patch("uaclient.config.UAConfig.read_cache")
    @mock.patch("uaclient.config.os.path.exists", return_value=True)
    def test_machine_token_overlay_json_decode_error(
        self, m_path, m_read_cache, m_load_file
    ):
        invalid_json_path = "machine-token-path"
        user_cfg = {"features": {"machine_token_overlay": invalid_json_path}}
        m_read_cache.return_value = self.machine_token_dict

        json_str = '{"directives": {"remoteServer": "overlay"}'
        m_load_file.return_value = json_str
        expected_msg = status.ERROR_JSON_DECODING_IN_FILE.format(
            error="Expecting ',' delimiter: line 1 column 43 (char 42)",
            file_path=invalid_json_path,
        )

        cfg = UAConfig(cfg=user_cfg)
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

import mock
import pytest

from uaclient.daemon.license_check import (
    check_license,
    get_polling_fn,
    should_poll,
)

M_PATH = "uaclient.daemon.license_check."


class TestCheckLicense:
    @mock.patch(M_PATH + "actions.auto_attach")
    @mock.patch(M_PATH + "_get_cloud", return_value=None)
    def test_not_on_cloud(self, m_get_cloud, m_auto_attach, FakeConfig):
        result = check_license(FakeConfig())
        assert result is None
        assert [] == m_auto_attach.call_args_list

    @mock.patch(M_PATH + "actions.auto_attach")
    @mock.patch(M_PATH + "_get_cloud")
    def test_no_license_present(self, m_get_cloud, m_auto_attach, FakeConfig):
        def fake_instance(cfg):
            fake = mock.MagicMock()
            fake.is_license_present = lambda: False
            return fake

        m_get_cloud.side_effect = fake_instance

        result = check_license(FakeConfig())
        assert result is None
        assert [] == m_auto_attach.call_args_list

    @mock.patch(M_PATH + "lock.SpinLock.__exit__")
    @mock.patch(M_PATH + "lock.SpinLock.__enter__")
    @mock.patch(M_PATH + "actions.auto_attach")
    @mock.patch(M_PATH + "_get_cloud")
    def test_auto_attach(
        self,
        m_get_cloud,
        m_auto_attach,
        _m_lock_enter,
        _m_lock_exit,
        FakeConfig,
    ):
        def fake_instance(cfg):
            fake = mock.MagicMock()
            fake.is_license_present = lambda: True
            return fake

        m_get_cloud.side_effect = fake_instance

        result = check_license(FakeConfig())
        assert result is None
        assert [mock.call(mock.ANY, mock.ANY)] == m_auto_attach.call_args_list


class TestShouldPoll:
    @mock.patch(M_PATH + "util.is_current_series_lts")
    @mock.patch(M_PATH + "config.UAConfig.write_cfg")
    @mock.patch(M_PATH + "util.is_config_value_true")
    @mock.patch(M_PATH + "_get_cloud", return_value=None)
    def test_not_on_cloud(
        self, m_get_cloud, m_util_is_true, _m_write_cfg, m_is_lts, FakeConfig
    ):
        cfg = FakeConfig()
        cfg.should_poll_for_licenses = True
        m_util_is_true.return_value = False
        m_is_lts.return_value = True

        result = should_poll(cfg)

        assert not result

    @pytest.mark.parametrize(
        "cfg_should_poll, cfg_disable_auto_attach, cfg_is_attached, is_lts,"
        " expected",
        (
            (True, False, False, True, True),
            (False, False, False, True, False),
            (True, True, False, True, False),
            (True, False, True, True, False),
            (True, False, False, False, False),
        ),
    )
    @mock.patch(M_PATH + "util.is_current_series_lts")
    @mock.patch(M_PATH + "config.UAConfig.write_cfg")
    @mock.patch(M_PATH + "util.is_config_value_true")
    @mock.patch(M_PATH + "_get_cloud", return_value=None)
    def test_static_checks(
        self,
        m_get_cloud,
        m_util_is_true,
        _m_write_cfg,
        m_is_lts,
        cfg_should_poll,
        cfg_disable_auto_attach,
        cfg_is_attached,
        is_lts,
        expected,
        FakeConfig,
    ):
        def fake_instance(cfg):
            fake = mock.MagicMock()
            fake.should_poll_for_license = lambda: True
            return fake

        m_get_cloud.side_effect = fake_instance

        if cfg_is_attached:
            cfg = FakeConfig.for_attached_machine()
        else:
            cfg = FakeConfig()

        cfg.should_poll_for_licenses = cfg_should_poll

        m_util_is_true.return_value = cfg_disable_auto_attach
        m_is_lts.return_value = is_lts

        result = should_poll(cfg)

        assert expected == result

    @pytest.mark.parametrize("cloud_ret", (True, False))
    @mock.patch(M_PATH + "util.is_current_series_lts")
    @mock.patch(M_PATH + "config.UAConfig.write_cfg")
    @mock.patch(M_PATH + "util.is_config_value_true")
    @mock.patch(M_PATH + "_get_cloud", return_value=None)
    def test_calls_cloud_should_poll(
        self,
        m_get_cloud,
        m_util_is_true,
        _m_write_cfg,
        m_is_lts,
        cloud_ret,
        FakeConfig,
    ):
        def fake_instance(cfg):
            fake = mock.MagicMock()
            fake.should_poll_for_license = lambda: cloud_ret
            return fake

        m_get_cloud.side_effect = fake_instance

        cfg = FakeConfig()
        cfg.should_poll_for_licenses = True
        m_util_is_true.return_value = False
        m_is_lts.return_value = True

        result = should_poll(cfg)

        assert cloud_ret == result


class TestGetPollingFn:
    @mock.patch(M_PATH + "_get_cloud", return_value=None)
    def test_not_on_cloud(self, m_get_cloud, FakeConfig):
        result = get_polling_fn(FakeConfig())
        assert result is None

    @mock.patch(M_PATH + "_get_cloud")
    def test_calls_cloud_get_polling_fn(self, m_get_cloud, FakeConfig):
        def fake_instance(cfg):
            fake = mock.MagicMock()
            fake.get_polling_fn = lambda: "test"
            return fake

        m_get_cloud.side_effect = fake_instance

        result = get_polling_fn(FakeConfig())
        assert result == "test"

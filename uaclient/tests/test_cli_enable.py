import mock

import pytest

from uaclient.cli import _perform_enable


class TestPerformEnable:

    @mock.patch('uaclient.cli.entitlements')
    def test_missing_entitlement_raises_keyerror(self, m_entitlements):
        """We raise a KeyError on missing entitlements

        (This isn't a problem because any callers of _perform_enable should
        already have rejected invalid names.)
        """
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {}

        with pytest.raises(KeyError):
            _perform_enable('entitlement', mock.Mock())

    @mock.patch('uaclient.cli.entitlements')
    def test_entitlement_instantiated_and_enabled(self, m_entitlements):
        m_entitlement_cls = mock.Mock()
        m_cfg = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            'testitlement': m_entitlement_cls,
        }

        ret = _perform_enable('testitlement', m_cfg)

        assert [mock.call(m_cfg)] == m_entitlement_cls.call_args_list

        m_entitlement = m_entitlement_cls.return_value
        assert [mock.call()] == m_entitlement.enable.call_args_list
        assert ret == m_entitlement.enable.return_value

import mock
import pytest

from uaclient.cli import action_disable


class TestDisable:

    @pytest.mark.parametrize('disable_return,return_code',
                             ((True, 0), (False, 1)))
    @mock.patch('uaclient.cli.entitlements')
    @mock.patch('uaclient.cli.os.getuid', return_value=0)
    def test_entitlement_instantiated_and_disabled(
            self, _m_getuid, m_entitlements, disable_return, return_code):
        m_entitlement_cls = mock.Mock()
        m_entitlement = m_entitlement_cls.return_value
        m_entitlement.disable.return_value = disable_return
        m_cfg = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            'testitlement': m_entitlement_cls,
        }

        args_mock = mock.Mock()
        args_mock.name = 'testitlement'

        ret = action_disable(args_mock, m_cfg)

        assert [mock.call(m_cfg)] == m_entitlement_cls.call_args_list

        expected_disable_call = mock.call()
        assert [expected_disable_call] == m_entitlement.disable.call_args_list
        assert return_code == ret

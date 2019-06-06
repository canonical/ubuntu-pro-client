import mock

from uaclient.testing.fakes import FakeConfig

import logging
import pytest

from uaclient.cli import _perform_enable, action_enable

M_PATH = 'uaclient.cli.'


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

    @pytest.mark.parametrize('silent_if_inapplicable', (True, False, None))
    @mock.patch('uaclient.cli.entitlements')
    def test_entitlement_instantiated_and_enabled(self, m_entitlements,
                                                  silent_if_inapplicable):
        m_entitlement_cls = mock.Mock()
        m_cfg = mock.Mock()
        m_entitlements.ENTITLEMENT_CLASS_BY_NAME = {
            'testitlement': m_entitlement_cls,
        }

        kwargs = {}
        if silent_if_inapplicable is not None:
            kwargs['silent_if_inapplicable'] = silent_if_inapplicable
        ret = _perform_enable('testitlement', m_cfg, **kwargs)

        assert [mock.call(m_cfg)] == m_entitlement_cls.call_args_list

        m_entitlement = m_entitlement_cls.return_value
        if silent_if_inapplicable:
            expected_enable_call = mock.call(silent_if_inapplicable=True)
        else:
            expected_enable_call = mock.call(silent_if_inapplicable=False)
        assert [expected_enable_call] == m_entitlement.enable.call_args_list
        assert ret == m_entitlement.enable.return_value

        assert 1 == m_cfg.status.call_count


class TestActionEnable:

    @pytest.mark.parametrize('caplog_text', [logging.DEBUG], indirect=True)
    @mock.patch(M_PATH + '_perform_enable')
    @mock.patch(M_PATH + 'contract.request_updated_contract')
    @mock.patch(M_PATH + 'os.getuid', return_value=0)
    def test_exits_nonzero_on_failed_contract_refresh(
            self, _, m_request_updated_contract, m_perform_enable,
            caplog_text):
        m_request_updated_contract.return_value = False  # failure to refresh
        account_name = 'test_account'
        cfg = FakeConfig.for_attached_machine(account_name=account_name)
        args = mock.MagicMock(name='livepatch')
        ret = action_enable(args, cfg)
        assert ret == 1
        expected_messages = [
            'DEBUG    Refreshing contracts prior to enable',
            'ERROR    Failure to refresh Ubuntu Advantage contracts.']
        for msg in expected_messages:
            assert msg in caplog_text()
        assert 0 == m_perform_enable.call_count

    @pytest.mark.parametrize('perform_enable_return', (True, False))
    @mock.patch(M_PATH + '_perform_enable')
    @mock.patch(M_PATH + 'contract.request_updated_contract')
    @mock.patch(M_PATH + 'os.getuid', return_value=0)
    def test_exit_code_based_on_success_of_perform_enable(
            self, _, m_request_updated_contract, m_perform_enable,
            perform_enable_return):
        m_perform_enable.return_value = perform_enable_return
        m_request_updated_contract.return_value = True  # successful refresh
        account_name = 'test_account'
        cfg = FakeConfig.for_attached_machine(account_name=account_name)
        args = mock.MagicMock(name='livepatch')
        ret = action_enable(args, cfg)
        exit_code = 0 if perform_enable_return else 1
        assert ret == exit_code

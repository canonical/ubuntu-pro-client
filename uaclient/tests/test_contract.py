import copy
import mock
import pytest

from uaclient.contract import (
    API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH,
    API_V1_TMPL_RESOURCE_MACHINE_ACCESS,
    process_entitlement_delta,
    request_updated_contract,
)
from uaclient import exceptions

from uaclient.testing.fakes import FakeConfig, FakeContractClient


M_PATH = 'uaclient.contract.'
M_REPO_PATH = 'uaclient.entitlements.repo.RepoEntitlement.'


class TestProcessEntitlementDeltas:
    def test_error_on_missing_entitlement_type(self):
        """Raise an error when neither dict contains entitlement type."""
        new_access = {'entitlement': {'something': 'non-empty'}}
        error_msg = (
            'Could not determine contract delta service type'
            ' {{}} {}'.format(new_access)
        )
        with pytest.raises(RuntimeError) as exc:
            process_entitlement_delta({}, new_access)
        assert error_msg == str(exc.value)

    def test_no_delta_on_equal_dicts(self):
        """No deltas are reported or processed when dicts are equal."""
        assert {} == process_entitlement_delta(
            {'entitlement': {'no': 'diff'}}, {'entitlement': {'no': 'diff'}}
        )

    @mock.patch(M_REPO_PATH + 'process_contract_deltas')
    def test_deltas_handled_by_entitlement_process_contract_deltas(
        self, m_process_contract_deltas
    ):
        """Call entitlement.process_contract_deltas to handle any deltas."""
        original_access = {'entitlement': {'type': 'esm'}}
        new_access = copy.deepcopy(original_access)
        new_access['entitlement']['newkey'] = 'newvalue'
        expected = {'entitlement': {'newkey': 'newvalue'}}
        assert expected == process_entitlement_delta(
            original_access, new_access
        )
        expected_calls = [
            mock.call(original_access, expected, allow_enable=False)
        ]
        assert expected_calls == m_process_contract_deltas.call_args_list

    @mock.patch(M_REPO_PATH + 'process_contract_deltas')
    def test_full_delta_on_empty_orig_dict(self, m_process_contract_deltas):
        """Process and report full deltas on empty original access dict."""
        # Limit delta processing logic to handle attached state-A to state-B
        # Fresh installs will have empty/unset
        new_access = {'entitlement': {'type': 'esm', 'other': 'val2'}}
        assert new_access == process_entitlement_delta({}, new_access)
        expected_calls = [mock.call({}, new_access, allow_enable=False)]
        assert expected_calls == m_process_contract_deltas.call_args_list

    @mock.patch(
        'uaclient.util.get_platform_info',
        return_value={'series': 'fake_series'},
    )
    @mock.patch(M_REPO_PATH + 'process_contract_deltas')
    def test_overrides_applied_before_comparison(
        self, m_process_contract_deltas, _
    ):
        old_access = {'entitlement': {'type': 'esm', 'some_key': 'some_value'}}
        new_access = {
            'entitlement': {
                'type': 'esm',
                'some_key': 'will be overridden',
                'series': {'fake_series': {'some_key': 'some_value'}},
            }
        }

        process_entitlement_delta(old_access, new_access)

        assert 0 == m_process_contract_deltas.call_count


class TestRequestUpdatedContract:

    refresh_route = API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH.format(
        contract='cid', machine='mid'
    )
    access_route_ent1 = API_V1_TMPL_RESOURCE_MACHINE_ACCESS.format(
        resource='ent1', machine='mid'
    )
    access_route_ent2 = API_V1_TMPL_RESOURCE_MACHINE_ACCESS.format(
        resource='ent2', machine='mid'
    )

    @mock.patch(M_PATH + 'UAContractClient')
    def test_attached_config_and_contract_token_runtime_error(self, client):
        """When attached, error if called with a contract_token."""

        def fake_contract_client(cfg):
            return FakeContractClient(cfg)

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(RuntimeError) as exc:
            request_updated_contract(cfg, contract_token='something')

        expected_msg = (
            'Got unexpected contract_token on an already attached machine'
        )
        assert expected_msg == str(exc.value)

    @mock.patch('uaclient.util.get_machine_id', return_value='mid')
    @mock.patch(M_PATH + 'UAContractClient')
    def test_user_facing_error_on_machine_token_refresh_failure(
        self, client, get_machine_id
    ):
        """When attaching, error on failure to refresh the machine token."""

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {
                self.refresh_route: exceptions.UserFacingError(
                    'Machine token refresh fail'
                ),
                self.access_route_ent1: exceptions.UserFacingError(
                    'Broken ent1 route'
                ),
            }
            return fake_client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine()
        with pytest.raises(exceptions.UserFacingError) as exc:
            request_updated_contract(cfg)

        assert 'Machine token refresh fail' == str(exc.value)

    @mock.patch('uaclient.util.get_machine_id', return_value='mid')
    @mock.patch(M_PATH + 'UAContractClient')
    def test_user_facing_error_on_service_token_refresh_failure(
        self, client, get_machine_id
    ):
        """When attaching, error on any failed specific service refresh."""

        machine_token = {
            'machineToken': 'mToken',
            'machineTokenInfo': {
                'contractInfo': {
                    'id': 'cid',
                    'resourceEntitlements': [
                        {'entitled': True, 'type': 'ent2'},
                        {'entitled': True, 'type': 'ent1'},
                    ],
                }
            },
        }

        def fake_contract_client(cfg):
            fake_client = FakeContractClient(cfg)
            fake_client._responses = {
                self.refresh_route: machine_token,
                self.access_route_ent1: exceptions.UserFacingError(
                    'Broken ent1 route'
                ),
                self.access_route_ent2: exceptions.UserFacingError(
                    'Broken ent2 route'
                ),
            }
            return fake_client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine(machine_token=machine_token)
        with pytest.raises(exceptions.UserFacingError) as exc:
            request_updated_contract(cfg)

        assert 'Broken ent1 route' == str(exc.value)

    @mock.patch(M_PATH + 'process_entitlement_delta')
    @mock.patch('uaclient.util.get_machine_id', return_value='mid')
    @mock.patch(M_PATH + 'UAContractClient')
    def test_attached_config_refresh_machine_token_and_services(
        self, client, get_machine_id, process_entitlement_delta
    ):
        """When attached, refresh machine token and entitled services.

        Processing service deltas are processed in a sorted order based on
        name to ensure operations occur the same regardless of dict ordering.
        """

        # resourceEntitlements specifically ordered reverse alphabetically
        # to ensure proper sorting for process_contract_delta calls below
        machine_token = {
            'machineToken': 'mToken',
            'machineTokenInfo': {
                'contractInfo': {
                    'id': 'cid',
                    'resourceEntitlements': [
                        {'entitled': False, 'type': 'ent2'},
                        {'entitled': True, 'type': 'ent1'},
                    ],
                }
            },
        }

        def fake_contract_client(cfg):
            client = FakeContractClient(cfg)
            # Note ent2 access route is not called
            client._responses = {
                self.refresh_route: machine_token,
                self.access_route_ent1: {
                    'entitlement': {
                        'entitled': True,
                        'type': 'ent1',
                        'new': 'newval',
                    }
                },
            }
            return client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine(machine_token=machine_token)
        assert None is request_updated_contract(cfg)
        assert machine_token == cfg.read_cache('machine-token')

        # Deltas are processed in a sorted fashion so that if enableByDefault
        # is true, the order of enablement operations is the same regardless
        # of dict key ordering.
        process_calls = [
            mock.call(
                {'entitlement': {'entitled': True, 'type': 'ent1'}},
                {
                    'entitlement': {
                        'entitled': True,
                        'type': 'ent1',
                        'new': 'newval',
                    }
                },
                allow_enable=False,
            ),
            mock.call(
                {'entitlement': {'entitled': False, 'type': 'ent2'}},
                {'entitlement': {'entitled': False, 'type': 'ent2'}},
                allow_enable=False,
            ),
        ]
        assert process_calls == process_entitlement_delta.call_args_list

import copy
import mock
import pytest

from uaclient.contract import (
    API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH,
    API_V1_TMPL_RESOURCE_MACHINE_ACCESS, process_entitlement_delta,
    request_updated_contract)

from uaclient.testing.fakes import FakeConfig, FakeContractClient


M_PATH = 'uaclient.contract.'
M_REPO_PATH = 'uaclient.entitlements.repo.RepoEntitlement.'


class TestProcessEntitlementDeltas:

    def test_error_on_missing_entitlement_type(self):
        """Raise an error when neither dict contains entitlement type."""
        error_msg = ('Could not determine contract delta service type %s %s' %
                     ({}, {'something': 'non-empty'}))
        with pytest.raises(RuntimeError, match=error_msg):
            process_entitlement_delta({}, {'something': 'non-empty'})

    def test_no_delta_on_equal_dicts(self):
        """No deltas are reported or processed when dicts are equal."""
        assert {} == process_entitlement_delta({'no': 'diff'}, {'no': 'diff'})

    @mock.patch(M_REPO_PATH + 'process_contract_deltas')
    def test_deltas_handled_by_entitlement_process_contract_deltas(
            self, m_process_contract_deltas):
        """Call entitlement.process_contract_deltas to handle any deltas."""
        original_access = {'entitlement': {'type': 'esm'}}
        new_access = copy.deepcopy(original_access)
        new_access['entitlement']['newkey'] = 'newvalue'
        expected = {'entitlement': {'newkey': 'newvalue'}}
        assert expected == process_entitlement_delta(
            original_access, new_access)
        expected_calls = [mock.call(original_access, expected)]
        assert expected_calls == m_process_contract_deltas.call_args_list

    @mock.patch(M_REPO_PATH + 'process_contract_deltas')
    def test_full_delta_on_empty_orig_dict(self, m_process_contract_deltas):
        """Process and report full deltas on empty original access dict."""
        # Limit delta processing logic to handle attached state-A to state-B
        # Fresh installs will have empty/unset
        new_access = {'entitlement': {'type': 'esm', 'other': 'val2'}}
        assert new_access == process_entitlement_delta({}, new_access)
        expected_calls = [mock.call({}, new_access)]
        assert expected_calls == m_process_contract_deltas.call_args_list


class TestRequestUpdatedContract:

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
            'Got unexpected contract_token on an already attached machine')
        assert expected_msg == str(exc.value)

    @mock.patch('uaclient.util.get_machine_id', return_value='mid')
    @mock.patch(M_PATH + 'UAContractClient')
    def test_attached_config_refresh_machine_token_and_services(
            self, client, get_machine_id):
        """When attached, refresh machine token and all enabled services."""

        refresh_route = API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH.format(
            contract='cid', machine='mid')
        access_route_ent1 = API_V1_TMPL_RESOURCE_MACHINE_ACCESS.format(
            resource='ent1', machine='mid')

        machine_token = {
            'machineToken': 'mToken',
            'machineTokenInfo': {'contractInfo': {
                'id': 'cid', 'resourceEntitlements': [
                    {'entitled': True, 'type': 'ent1'},
                    {'entitled': False, 'type': 'ent2'}]}}}

        def fake_contract_client(cfg):
            client = FakeContractClient(cfg)
            # Note ent2 access route is not called
            client._responses = {
                refresh_route: machine_token,
                access_route_ent1: {
                    'entitlement': {'entitled': True, 'type': 'ent1'}}}
            return client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine(machine_token=machine_token)
        assert True is request_updated_contract(cfg)
        assert machine_token == cfg.read_cache('machine-token')
        # Redact public content
        assert (
            '<REDACTED>' == cfg.read_cache(
                'public-machine-token')['machineToken'])

import mock
import pytest

from uaclient.contract import (
    API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH, request_updated_contract)

from uaclient.testing.fakes import FakeConfig, FakeContractClient


M_PATH = 'uaclient.contract.'


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
        """When attached, refresh machine token and all entitlements."""

        refresh_route = API_V1_TMPL_CONTEXT_MACHINE_TOKEN_REFRESH.format(
            contract='cid', machine='mid')

        machine_token = {
            'machineToken': 'mToken',
            'machineTokenInfo': {'contractInfo': {
                'id': 'cid', 'resourceEntitlements': [
                    {'entitled': True, 'type': 'ent1'},
                    {'entitled': False, 'type': 'ent2'}]}}}

        def fake_contract_client(cfg):
            client = FakeContractClient(cfg)
            client._responses = {refresh_route: machine_token}
            return client

        client.side_effect = fake_contract_client
        cfg = FakeConfig.for_attached_machine(machine_token=machine_token)
        assert True is request_updated_contract(cfg)
        assert machine_token == cfg.read_cache('machine-token')
        # Redact public content
        assert (
            '<REDACTED>' == cfg.read_cache(
                'public-machine-token')['machineToken'])

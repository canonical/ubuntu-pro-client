import mock

import pytest

from uaclient import config
from uaclient.entitlements.repo import RepoEntitlement


class RepoTestEntitlement(RepoEntitlement):
    """Subclass so we can test shared repo functionality"""

    def disable(self, *args, **kwargs):
        pass


class TestRepoEnable:

    @pytest.mark.parametrize('silent_if_inapplicable', (True, False, None))
    @mock.patch.object(RepoTestEntitlement, 'can_enable', return_value=False)
    def test_enable_passes_silent_if_inapplicable_through(
            self, m_can_enable, caplog_text, tmpdir, silent_if_inapplicable):
        """When can_enable returns False enable returns False."""
        cfg = config.UAConfig(cfg={'data_dir': tmpdir.strpath})
        entitlement = RepoTestEntitlement(cfg)

        kwargs = {}
        if silent_if_inapplicable is not None:
            kwargs['silent_if_inapplicable'] = silent_if_inapplicable
        entitlement.enable(**kwargs)

        expected_call = mock.call(silent=bool(silent_if_inapplicable))
        assert [expected_call] == m_can_enable.call_args_list

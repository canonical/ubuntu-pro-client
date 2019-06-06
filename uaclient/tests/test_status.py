import pytest

from uaclient import config
from uaclient.status import format_tabular, TxtColor


class TestFormatTabular:

    @pytest.mark.parametrize('support_level,expected_colour', [
        ('n/a', TxtColor.DISABLEGREY),
        ('essential', TxtColor.OKGREEN),
        ('standard', TxtColor.OKGREEN),
        ('advanced', TxtColor.OKGREEN),
        ('something else', None),
    ])
    def test_support_colouring(self, support_level, expected_colour):
        status = config.DEFAULT_STATUS.copy()
        status['techSupportLevel'] = support_level

        # The following are required so we don't get an "unattached" error
        status['attached'] = True
        status['account'] = 'account'
        status['subscription'] = 'subscription'
        status['expires'] = 'expires'

        tabular_output = format_tabular(status)

        expected_string = 'Technical support level: {}'.format(
            support_level if not expected_colour else
            expected_colour + support_level + TxtColor.ENDC)
        assert expected_string in tabular_output

import mock
import pytest

from uaclient import config
from uaclient.status import format_tabular, TxtColor


class TestFormatTabular:

    @pytest.mark.parametrize('support_level,expected_colour,istty', [
        ('n/a', TxtColor.DISABLEGREY, True),
        ('essential', TxtColor.OKGREEN, True),
        ('standard', TxtColor.OKGREEN, True),
        ('advanced', TxtColor.OKGREEN, True),
        ('something else', None, True),
        ('n/a', TxtColor.DISABLEGREY, True),
        ('essential', None, False),
        ('standard', None, False),
        ('advanced', None, False),
        ('something else', None, False),
        ('n/a', None, False),

    ])
    @mock.patch('sys.stdout.isatty')
    def test_support_colouring(self, m_isatty, support_level, expected_colour,
                               istty):
        status = config.DEFAULT_STATUS.copy()
        status['techSupportLevel'] = support_level

        # The following are required so we don't get an "unattached" error
        status['attached'] = True
        status['account'] = 'account'
        status['subscription'] = 'subscription'
        status['expires'] = 'expires'

        m_isatty.return_value = istty
        tabular_output = format_tabular(status)

        expected_string = 'Technical support level: {}'.format(
            support_level if not expected_colour else
            expected_colour + support_level + TxtColor.ENDC)
        assert expected_string in tabular_output

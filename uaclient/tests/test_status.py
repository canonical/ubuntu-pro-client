import mock
import pytest

from uaclient import config
from uaclient.status import format_tabular, TxtColor


@pytest.fixture
def status_dict_attached():
    status = config.DEFAULT_STATUS.copy()

    # The following are required so we don't get an "unattached" error
    status['attached'] = True
    status['account'] = 'account'
    status['subscription'] = 'subscription'
    status['expires'] = 'expires'

    return status


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
                               istty, status_dict_attached):
        status_dict_attached['techSupportLevel'] = support_level

        m_isatty.return_value = istty
        tabular_output = format_tabular(status_dict_attached)

        expected_string = 'Technical support level: {}'.format(
            support_level if not expected_colour else
            expected_colour + support_level + TxtColor.ENDC)
        assert expected_string in tabular_output

    @pytest.mark.parametrize('origin', ['free', 'not-free'])
    def test_header_alignment(self, origin, status_dict_attached):
        status_dict_attached['origin'] = origin
        tabular_output = format_tabular(status_dict_attached)
        colon_idx = None
        for line in tabular_output.splitlines():
            if ':' not in line:
                # This isn't a header line
                continue
            if colon_idx is None:
                # This is the first header line, record where the colon is
                colon_idx = line.index(':')
                continue
            # Ensure that the colon in this line is aligned with previous ones
            assert line.index(':') == colon_idx

    @pytest.mark.parametrize('origin,expected_headers', [
        ('free', ('Account', 'Subscription')),
        ('not-free', ('Account', 'Subscription', 'Valid until',
                      'Technical support level')),
    ])
    def test_correct_header_keys_included(
            self, origin, expected_headers, status_dict_attached):
        status_dict_attached['origin'] = origin

        tabular_output = format_tabular(status_dict_attached)

        headers = [line.split(':')[0].strip()
                   for line in tabular_output.splitlines()
                   if ':' in line]
        assert list(expected_headers) == headers

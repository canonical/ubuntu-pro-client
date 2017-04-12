import imp
import os
from unittest import TestCase

script_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'ubuntu-advantage')
ubuntu_advantage = imp.load_source('ubuntu_advantage', script_path)


class UbuntuAdvantageTests(TestCase):

    def test_get_args_enable(self):
        """The 'enable-esm' arg is called with a token to enable the repo."""
        args = ubuntu_advantage.get_args(['enable-esm', 'user:pass'])
        self.assertEqual('enable-esm', args.action)
        self.assertEqual('user:pass', args.token)

    def test_get_args_disable(self):
        """The 'disable-esm' action can be called."""
        args = ubuntu_advantage.get_args(['disable-esm'])
        self.assertEqual('disable-esm', args.action)

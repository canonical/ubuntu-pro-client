from __future__ import print_function
import imp
import os

from fixtures import TestWithFixtures, TempDir

script_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'ubuntu-advantage')
ubuntu_advantage = imp.load_source('ubuntu_advantage', script_path)


class UbuntuAdvantageTest(TestWithFixtures):

    def setUp(self):
        super(UbuntuAdvantageTest, self).setUp()
        self.tempdir = self.useFixture(TempDir())
        self.messages = []
        self.print = lambda message: self.messages.append(message)

    def test_get_args_enable(self):
        """The 'enable-esm' arg is called with a token to enable the repo."""
        args = ubuntu_advantage.get_args(['enable-esm', 'user:pass'])
        self.assertEqual('enable-esm', args.action)
        self.assertEqual('user:pass', args.token)

    def test_get_args_disable(self):
        """The 'disable-esm' action can be called."""
        args = ubuntu_advantage.get_args(['disable-esm'])
        self.assertEqual('disable-esm', args.action)

    def test_get_list_file(self):
        """get_list_file returns the name of the sources.list.d file."""
        self.assertEqual(
            ubuntu_advantage.get_list_file(),
            '/etc/apt/sources.list.d/ubuntu-esm-precise.list')

    def test_write_list_file(self):
        """write_list_file writes the sources.list.d file."""
        list_file = self.tempdir.join('sample.list')
        ubuntu_advantage.write_list_file(list_file, 'user:pass')
        with open(list_file) as fh:
            content = fh.read()
        expected = (
            'deb https://user:pass@extended.security.staging.ubuntu.com'
            '/ubuntu precise main\n'
            '# deb-src https://user:pass@extended.security.staging.ubuntu.com'
            '/ubuntu precise main\n')
        self.assertEqual(expected, content)

    def test_enable_esm(self):
        """enable_esm adds the repository to sources lists."""
        ubuntu_advantage.enable_esm(
            'user:pass', lists_dir=self.tempdir.path, print=self.print)
        list_file = self.tempdir.join('ubuntu-esm-precise.list')
        with open(list_file) as fh:
            content = fh.read()
        expected = (
            'deb https://user:pass@extended.security.staging.ubuntu.com'
            '/ubuntu precise main\n'
            '# deb-src https://user:pass@extended.security.staging.ubuntu.com'
            '/ubuntu precise main\n')
        self.assertEqual(expected, content)
        # a message is printed out
        self.assertEqual(
            ['Ubuntu ESM repository enabled.'
             '  Run "sudo apt-get update" to update lists.'],
            self.messages)

    def test_disable_esm(self):
        """disabl_esm renames the lists file as .save."""
        ubuntu_advantage.enable_esm(
            'user:pass', lists_dir=self.tempdir.path, print=self.print)
        list_file = self.tempdir.join('ubuntu-esm-precise.list')
        with open(list_file) as fh:
            original_content = fh.read()

        self.messages = []
        ubuntu_advantage.disable_esm(
            lists_dir=self.tempdir.path, print=self.print)
        # the file has moved
        self.assertFalse(os.path.exists(list_file))
        # the original content is still there
        with open(list_file + '.save') as fh:
            content = fh.read()
        self.assertEqual(original_content, content)
        # a message is printed out
        self.assertEqual(
            ['Ubuntu ESM repository disabled.'
             '  Run "sudo apt-get update" to update lists.'],
            self.messages)

    def test_disable_esm_not_enabled(self):
        """If the list is not there, disable_esm is a no-op."""
        list_file = self.tempdir.join('ubuntu-esm-precise.list')
        ubuntu_advantage.disable_esm(
            lists_dir=self.tempdir.path, print=self.print)
        self.assertFalse(os.path.exists(list_file))
        self.assertFalse(os.path.exists(list_file + '.save'))
        # a message is printed out
        self.assertEqual(
            ['Ubuntu ESM repository was not enabled.'], self.messages)

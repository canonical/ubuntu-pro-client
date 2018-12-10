import functools
import logging
import six
import shutil
import tempfile
import unittest2


class TestCase(unittest2.TestCase):

    with_logs = False

    def setUp(self):
        super(TestCase, self).setUp()
        if self.with_logs:
            # Create a log handler so unit tests can search expected logs.
            self.logger = logging.getLogger()
            self._logs = six.StringIO()
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            handler = logging.StreamHandler(self._logs)
            handler.setFormatter(formatter)
            self.old_handlers = self.logger.handlers
            self.logger.handlers = [handler]

    def tearDown(self):
        if self.with_logs:
            # Remove the handler we setup
            logging.getLogger().handlers = self.old_handlers
        super(TestCase, self).tearDown()

    @property
    def logs(self):
        """Return the contents of logs written during the unit test run."""
        if not self.with_logs:
            raise AssertionError(
                'Cannot reference test.logs when with_logs == False')
        return self._logs.getvalue()

    def tmp_dir(self, dir=None):
        if dir is None:
            tmpd = tempfile.mkdtemp(
                prefix='uaclient-%s.' % self.__class__.__name__)
        else:
            tmpd = tempfile.mkdtemp(dir=dir)
        self.addCleanup(functools.partial(shutil.rmtree, tmpd))
        return tmpd

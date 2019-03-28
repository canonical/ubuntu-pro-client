import functools
import os
import shutil
import tempfile
import unittest


class TestCase(unittest.TestCase):

    def tmp_dir(self, dir=None):
        if dir is None:
            tmpd = tempfile.mkdtemp(
                prefix='uaclient-%s.' % self.__class__.__name__)
        else:
            tmpd = tempfile.mkdtemp(dir=dir)
        self.addCleanup(functools.partial(shutil.rmtree, tmpd))
        return tmpd

    def tmp_path(self, path, dir=None):
        # return an absolute path to 'path' under dir.
        # if dir is None, one will be created with tmp_dir()
        # the file is not created or modified.
        if dir is None:
            dir = self.tmp_dir()
        return os.path.normpath(os.path.abspath(os.path.join(dir, path)))

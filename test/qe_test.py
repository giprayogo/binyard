#!/usr/bin/env python
# autorunning qe relax/vc-relax

from binyard.autorunner import print_args
from binyard.autorunner import timestamp
from binyard.autorunner_qe_opt import QEAutorunner
import os
import re
import fnmatch
import subprocess
import inspect
import argparse
import sys

import unittest

# for debugging program logic
# all 'active' functions, calling fetch, toss, etc., are disabled.
class QEAutorunnerDebug(QEAutorunner):
    _FETCHING = 'fetching'
    _QDELING = 'qdeling'
    _TOSSING = 'tossing'
    _UPDATING = 'updating'

    # delete?
    def __init__(self, *args, **kwargs):
        super(QEAutorunnerDebug, self).__init__(*args, **kwargs)

    # nullify all 'active' functions
    def qdel(self):
        super(QEAutorunnerDebug, self)._printout(self._QDELING)
        inspect.getsource(super(QEAutorunnerDebug, self).qdel)

    def toss(self):
        super(QEAutorunnerDebug, self)._printout(self._TOSSING)
        inspect.getsource(super(QEAutorunnerDebug, self).toss)

    def fetch(self):
        super(QEAutorunnerDebug, self)._printout(self._FETCHING)
        inspect.getsource(super(QEAutorunnerDebug, self).fetch)

    def update_files(self):
        super(QEAutorunnerDebug, self)._printout(self._UPDATING)
        inspect.getsource(super(QEAutorunnerDebug, self).update_files)

class TestQE(unittest.TestCase):
    # I'm going to rethink where this is supposed to be located in
    _TESTDIR = '/mnt/lustre/toBeSync/genki/git-repos/binyard/test/qe_files'
    _INTERVAL = 3

    def setUp(self):
        testdir = TestQE._TESTDIR
        interval = TestQE._INTERVAL
        self.assertEqual(testdir, '/mnt/lustre/toBeSync/genki/git-repos/binyard/test/qe_files')
        os.chdir(TestQE._TESTDIR)

        jsses = [ x for x in os.listdir('.') if fnmatch.fnmatch(x, '*.jss') ]
        self.assertEqual(len(jsses), 1)
        toss_string = jsses[0].replace('.jss', '')

        self.auto = QEAutorunnerDebug(toss_string, count=0, interval=interval, outstream=None)


    # I do think that each tests here can be splitted into 3 functions
    def test_job_finished(self):
        # The output file is there, so this should return True
        self.assertEqual(self.auto.job_finished(), True)

    def test_next_file(self):
        count = self.auto.count
        self.assertEqual(self.auto.next_file('input.in', True), 'input.in.'+str(count))
        self.assertEqual(self.auto.count, count + 1)
        self.assertEqual(self.auto.next_file('input.in', False), 'input.in.'+str(count+1))
        self.assertEqual(self.auto.count, count + 1)
#        auto.toss()
#        auto.run()


if __name__ == '__main__':
    unittest.main()

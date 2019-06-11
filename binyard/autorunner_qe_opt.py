#!/usr/bin/env python
# autorunning qe relax/vc-relax

from binyard.autorunner import Autorunner2
from binyard.autorunner import print_args
from binyard.autorunner import timestamp
from binyard.fileio import parse
import os
import re
import fnmatch
import subprocess
import inspect
import argparse
import sys

class QEAutorunner(Autorunner2):
    # non-changable class variables
    _OPTIMIZED = 'atomic positions/cell parameters has been optimized'
    _FAIL_SUBMIT = 'qsub failure'
    _QE_CRASH = 'QE has encountered an error'
    _RUNNING = 'job is running'
    _FINISHED = 'job has been finished'
    _COUNT_FORMAT = 'current count={0}'

    # super-inherited functions
    # constructor; the outstream was originally implemented due to annoying redirection behaviour
    # when working with a perl script (actually caused by fetch)
    def __init__(self, toss_args=None, count=0, input_file='input.in', output_file='out.o', *args, **kwargs):
        super(QEAutorunner, self).__init__(*args, **kwargs)
        if toss_args is None:
            raise ValueError("must set toss arguments")
        self.toss_args = toss_args
        self.count = count
        self.input_file = input_file
        self.output_file = output_file

    # sensing for re-submit
    def _sensor(self):
        done = False
        try:
            self.fetch()
            if self.job_finished():
                super(QEAutorunner, self)._printout(self._FINISHED)
                done = True
            else:
                super(QEAutorunner, self)._printout(self._RUNNING)
        except Exception:
            raise
        return done

    @timestamp
    @print_args
    def _terminator(self, *args, **kwargs):
        # do not fetch since some files may get deleted
        self.qdel()
        super(QEAutorunner, self)._terminator(*args, **kwargs)

    @timestamp
    @print_args
    def _actuator(self):
        self.update_files()
        self.toss()

    # child-only functions
    # public
    def qdel(self):
        super(QEAutorunner, self)._printout('qdel')
        subprocess.call(['qdel'])

    # TODO: I need to define correct behaviour in case of qstat
    # there is curently one hole in which output file is not created,
    # and everything stops, but no crash informations.
    #def qs(self):
    #    cluster = self.toss_args.split('.')[0]
    #    with open('JobNumber', 'r') as fh:
    #        jobnumber = fh.read().strip()
    #    qs = subprocess.call(['qs', cluster])

    def toss(self):
        super(QEAutorunner, self)._printout(self.toss_args)
        subprocess.call(['m_toss.pl', self.toss_args])

    def fetch(self):
        #TODO: somehow generalize this
        cmd = ['m_fetch.py', '--exclude', 'out', '--exclude', '*.log']
        super(QEAutorunner, self)._printout(' '.join(cmd))
        subprocess.call(cmd)

    def update_files(self):
        super(QEAutorunner, self)._printout(self._COUNT_FORMAT.format(self.count))
        subprocess.call(['extract_final.py'])
        # TODO: make these as user input
        mv_in_file = ['mv', self.input_file, self.next_file(self.input_file, self.count) ]
        print(' '.join(mv_in_file))
        subprocess.call(mv_in_file)
        mv_out_file = ['mv', self.output_file, self.next_file(self.output_file, self.count) ]
        print(' '.join(mv_out_file))
        subprocess.call(mv_out_file)
        subprocess.call(['mv', 'auto_final.in', 'input.in'])

    def next_file(self, pattern, count):
        self.count += 1
        return pattern + '.' + str(count)

    @print_args
    def job_finished(self):
        done = False
        #TODO: instead of simply out, read qe's outdir
        try:
            if os.stat('JobNumber').st_size == 0:
                raise Exception(self._FAIL_SUBMIT)
        except IOError:
            # in any case if there are no JobNumber the toss is presumed to has been failed
            raise Exception(self._FAIL_SUBMIT)
        if 'CRASH' in os.listdir('.'):
            raise Exception(self._QE_CRASH)
        try:
            with open('out.o', 'r') as fh:
                text = fh.read()
                if 'stopping ...' in text:
                    raise Exception(self._QE_CRASH)
                if 'Begin final coordinates' in text:
                    raise Exception(self._OPTIMIZED)
                if 'JOB DONE' in text:
                    done = True
        except IOError:
            # TODO: also check job queues
            pass # if job is queued; there will not be any output files
        super(QEAutorunner, self)._printout('job_finished return as : {0}'.format(done))
        return done

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('toss_string', type=str, default=None, nargs='?')
    parser.add_argument('--interval', '-i', type=int, required=True)
    parser.add_argument('--count', '-c', type=int, default=0)
    parser.add_argument('--logfile', '-l', default=None)
    args = parser.parse_args()

    # sometimes we want to process the arguments; this is a perhaps better practice
    toss_string = args.toss_string
    interval = args.interval
    count = args.count
    logfile = args.logfile

    if toss_string is None:
        jsses = [ x for x in os.listdir('.') if fnmatch.fnmatch(x, '*.jss') ]
        assert len(jsses) == 1
        toss_string = jsses[0].replace('.jss', '')
    auto = QEAutorunner(toss_args=toss_string, count=count, interval=interval, outstream=logfile)
    # do initial tosses
    auto.toss()
    auto.run()

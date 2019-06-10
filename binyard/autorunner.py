#!/usr/bin/env python
# autorunning helpers
# structure not finalized!
from __future__ import print_function
from threading import Timer
import time
import re
import fnmatch
import os
import sys
import signal


# Exit clauses, implemented as Exceptions
class OldError(Exception):
    pass

class ReturnNotZeroError(Exception):
    pass

class JobTerminationError(Exception):
    pass

class EnoughSampleError(Exception):
    pass


# Wrappers
# TODO: move under its own file
# Remember to RETURN the functions
# only accept single *args!
# default 'old' to be older than 1 hour
def print_args(func):
    def printed(*args, **kwargs):
        print('function:{0}; args:{1}; kwargs{2}'.format(func.__name__, args, kwargs))
        return func(*args, **kwargs)
    return printed

def timestamp(func):
    def stamped(*args, **kwargs):
        print(time.ctime())
        return func(*args, **kwargs)
    return stamped

# the default walltime in bgq + some leeway
def not_old(_func=None, threshold=7500):
    def oldchecking(func):
        def oldchecked(*args, **kwargs):
            mtime = os.stat(*args).st_mtime
            if time.time() - mtime > threshold:
                raise OldError
            return func(*args, **kwargs)
        return oldchecked
    if _func is None:
        return oldchecking
    else:
        return oldchecking(_func)


def latest(_=None, pattern=''):
    def inject(func):
        def injected(*args, **kwargs):
            file_list = sorted([ x for x in os.listdir('.') if fnmatch.fnmatch(x, pattern) ],
                key=lambda x: os.stat(x).st_mtime)
            return func(file_list[-1], *args, **kwargs)
        return injected
    if _ is None:
        return inject
    else:
        return inject(_)


def dmc_dat(_=None, start=5):
    def resolve(regex_match):
        if regex_match:
            return regex_match.group(0)
        return ''
    def serie(filename):
        return int(resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s'))
    
    def inject(func):
        def injected(*args, **kwargs):
            dmc_dats = sorted(sorted([ x for x in os.listdir('.')
                if '.dmc.dat' in x and not '.swp' in x and serie(x) >= start  ],
                key=twist), key=series)
            return func(dmc_dats, *args, **kwargs)
        return injected

    if _ is None:
        return inject 
    else:
        return inject(_)


# Used for sorting
# TODO: should these be grouped together?
def series(filename):
    """Get series number from scalar filename"""
    return resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s')

def twist(filename):
    """Get twist number from scalar filename"""
    return resolve(re.search(r'\-tw[0-9]+\.', filename)).strip('.').strip('s')


# to exit, sensor function must raise Exceptions
class Autorunner(object):
    def __init__(self, sensor, actuator):
        self.sensor = sensor # callable, return boolean
        self.actuator = actuator # callable, return not checked

    @print_args
    def run(self, interval=None):
        if interval is None:
            interval = self.interval
        self.interval = interval
        if self.sensor():
            self.actuator()
        print('waiting {0} seconds'.format(interval))
        Timer(interval, self.run).start()

# the way to use it is by EXTENDING this class
class Autorunner2(object):
    # things you will EXTEND/OVERWRITE
    def __init__(self, interval, outstream=None, errstream=sys.stderr):
        self.interval = interval
        self.outstream = outstream
        signal.signal(signal.SIGINT, self._quit)
        signal.signal(signal.SIGTERM, self._quit)
        self._printout('PID: {0}'.format(os.getpid()))

    # sensor for actuation
    def _sensor(self):
        self._printerr('Not implemented')
        return True

    # what you are automatically doing
    def _actuator(self):
        self._printerr('Not implemented')
        pass

    # when exiting what do you want to do
    @timestamp
    def _terminator(self):
        pass

    def _quit(self, signum=1, frame=None):
        self._terminator()
        sys.exit(signum)

    def run(self):
        try:
            if self._sensor():
                self._actuator()
        except Exception as e:
            self._terminator()
            raise
        self._printout('waiting {0} seconds'.format(self.interval))
        Timer(self.interval, self.run).start()


    # things you can use
    def _printout(self, message):
        if self.outstream is None:
            print(message, file=sys.stdout)
        else:
            with open(self.outstream, 'a') as fh:
                print(message, file=fh)

    def _printerr(self, message):
        print(message, file=self.errstream)


def done_cobaltlog(filename):
    #print('cobalt log: {0}'.format(filename))
    with open(filename, 'r') as log:
        content = log.read()
        #jobid = re.search(r'(?<=jobid) [0-9]+', content).group()
        #print('Jobid: {0}'.format(jobid))

        if 'task completed normally' in content:
            # completion signal
            #print('---task completed; checking return code')
            if 'exit code of 0' in content:
                #print('---exit code 0; continue')
                return True
            else:
                # always exit if exit code is not 0
                raise ReturnNotZeroError

        if 'maximum execution time exceeded' in content:
            raise JobTerminationError

        #print('---job still running; continue waiting')
        return False


def resolve(regex_match):
    """Return regex match string or empty string if no matches"""
    if regex_match:
        return regex_match.group(0)
    return ''

def nline(filename):
    with open(filename, 'r') as fh:
        return sum(1 for _ in fh)

def nsample(filenames):
    """Raise EnoughSampleError if target number of samples is satisfied;
       Otherwise return True"""
    #print(filenames)

    scalar = {}
    for filename in filenames:
        twist = resolve(re.search(r'tw[0-9]+', filename))
        scalar.setdefault(twist, {})
        scalar[twist].setdefault('filenames', [])
        scalar[twist]['filenames'].append(filename)
        scalar[twist].setdefault('nline', 0)
        scalar[twist]['nline'] += nline(filename) - 1 # the first line is a header TODO: proper header detection

    return [ x['nline'] for x in list(scalar.values()) ]


def check_nsample(filenames, target):
    #print('---checking number of samples')
    nsamples = nsample(filenames)
    if sum(nsamples) > target:
        raise EnoughSampleError
    #print('---insufficient number of samples')
    return True

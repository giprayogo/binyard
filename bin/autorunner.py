#!/usr/bin/env python
# autorunning helpers
# structure not finalized!
import threading
from threading import Timer
import time
import datetime
import re
import fnmatch
import os


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
# Remember to RETURN the functions
# only accept single *args!
# default 'old' to be older than 1 hour
def not_old(_func=None, threshold=3600):
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


def print_args(func):
    def printed(*args, **kwargs):
        print('function: {0}'.format(func.__name__))
        print('args: {0}'.format(args))
        print('kwargs: {0}'.format(kwargs))
        return func(*args, **kwargs)
    return printed


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
def series(filename):
    """Get series number from scalar filename"""
    return resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s')

def twist(filename):
    """Get twist number from scalar filename"""
    return resolve(re.search(r'\-tw[0-9]+\.', filename)).strip('.').strip('s')


# to exit, sensor function must raise Exceptions
class Autorunner():
    def __init__(self, sensor, actuator):
        self.sensor = sensor # callable, return boolean
        self.actuator = actuator # callable, return not checked

    def run(self, interval=None):
        if interval is None:
            interval = self.interval
        self.interval = interval
        if self.sensor():
            self.actuator()
        print(datetime.datetime.now())
        print('waiting {0} seconds'.format(interval))
        threading.Timer(interval, self.run).start()
        #print(datetime.datetime.now())
        #print('waiting {0} seconds'.format(interval))


def done_cobaltlog(filename):
    print('cobalt log: {0}'.format(filename))
    with open(filename, 'r') as log:
        content = log.read()
        jobid = re.search(r'(?<=jobid) [0-9]+', content)
        print('Jobid: {0}'.format(jobid))

        if 'task completed normally' in content:
            # completion signal
            print('---task completed; checking return code')
            if 'exit code of 0' in content:
                print('---exit code 0; continue')
                return True
            else:
                # always exit if exit code is not 0
                raise ReturnNotZeroError

        if 'maximum execution time exceeded' in content:
            raise JobTerminationError

        print('---job still running; continue waiting')
        return False


def resolve(regex_match):
    """Return regex match string or empty string if no matches"""
    if regex_match:
        return regex_match.group(0)
    return ''


def nline(filename):
    with open(filename, 'r') as fh:
        return sum(1 for _ in fh)


@print_args
def check_nsample(filenames, target):
    """Raise EnoughSampleError if target number of samples is satisfied;
       Otherwise return True"""
    print(filenames)
    
    scalar = {}
    for filename in filenames:
        twist = resolve(re.search(r'tw[0-9]+', filename))
        scalar.setdefault(twist, {})
        scalar[twist].setdefault('filenames', [])
        scalar[twist]['filenames'].append(filename)
        scalar[twist].setdefault('nline', 0)
        scalar[twist]['nline'] += nline(filename)

    print('---checking number of samples')
    nlines = [ x['nline'] for x in list(scalar.values()) ]
    if min(nlines) > target:
        raise EnoughSampleError
    print('---insufficient number of samples')
    return True

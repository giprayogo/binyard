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
    """ Wrapper for injecting dmc.dat files into first argument of a function;
    Allow specification of starting *scalar/dmc.dat series, default to 005 """
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


def qmcpack_output(_=None, start=5):
    """ Wrapper for injecting qmcpack (succesful) output file into the first argument
    of a function """
    def resolve(regex_match):
        if regex_match:
            return regex_match.group(0)
        return ''
    def serie(filename):
        try:
            return int(resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s'))
        except ValueError: # happens when no series/individual run
            return 0 # so that it will not be included

    def inject(func):
        def injected(*args, **kwargs):
            qmcpack_outputs = sorted(sorted([ x for x in os.listdir('.')
                #if '.qmc.xml' in x and not '.swp' in x and serie(x) >= start  ],
                if resolve(re.search('.qmc$', x))
                and not '.swp' in x and serie(x) >= start  ],
                key=twist), key=series)
            # something
            return func(qmcpack_outputs, *args, **kwargs)
        return injected

    if _ is None:
        return inject
    else:
        return inject(_)

    return injected


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


#class UnifiedAutorunner(Autorunner2):
#    # non-changable class variables
#    _FAIL_SUBMIT = 'qsub failure'
#    _RUNNING = 'job is running'
#    _FINISHED = 'job has been finished'
#
#    # super-inherited functions
#    # constructor; the outstream was originally implemented due to annoying redirection behaviour
#    # when working with a perl script (actually caused by fetch)
#    def __init__(self, toss_args=None,  input_file='input.in', output_file='out.o', *args, **kwargs):
#        super(QEAutorunner, self).__init__(*args, **kwargs)
#        if toss_args is None:
#            raise ValueError("must set toss arguments")
#        self.toss_args = toss_args
#        self.input_file = input_file
#        self.output_file = output_file
#
#    # sensing for re-submit
#    def _sensor(self):
#        done = False
#        try:
#            self.fetch()
#            if self.job_finished():
#                super(QEAutorunner, self)._printout(self._FINISHED)
#                done = True
#            else:
#                super(QEAutorunner, self)._printout(self._RUNNING)
#        except Exception:
#            raise
#        return done
#
#    @timestamp
#    @print_args
#    def _terminator(self, *args, **kwargs):
#        # do not fetch since some files may get deleted
#        self.qdel()
#        super(QEAutorunner, self)._terminator(*args, **kwargs)
#
#    @timestamp
#    @print_args
#    def _actuator(self):
#        self.update_files()
#        self.toss()
#
#    # child-only functions
#    # public
#    def qdel(self):
#        super(QEAutorunner, self)._printout('qdel')
#        subprocess.call(['qdel'])
#
#    #def qs(self):
#    #    cluster = self.toss_args.split('.')[0]
#    #    with open('JobNumber', 'r') as fh:
#    #        jobnumber = fh.read().strip()
#    #    qs = subprocess.call(['qs', cluster])
#
#    def toss(self, args):
#        super(QEAutorunner, self)._printout(self.toss_args)
#        subprocess.call(['m_toss.pl', args])
#
#    def fetch(self, args):
#        #TODO: somehow generalize this
#        cmd = ['m_fetch.py', '--exclude', 'out', '--exclude', '*.log']
#        cmd.extend(args)
#        super(QEAutorunner, self)._printout(' '.join(cmd))
#        subprocess.call(cmd)
#
#    #@print_args
#    #def printed_call(self, args, *other_args, **kwargs):
#    #    print(' '.join(args))
#    #    return subprocess.call(args=args, *other_args, **kwargs)
#
#    def update_files(self):
#        super(QEAutorunner, self)._printout(self._COUNT_FORMAT.format(self.count))
#        subprocess.call(['extract_final.py'])
#        # TODO: make these as user input
#        mv_in_file = ['mv', self.input_file, self.next_file(self.input_file, False) ]
#        print(' '.join(mv_in_file))
#        subprocess.call(mv_in_file)
#        mv_out_file = ['mv', self.output_file, self.next_file(self.output_file, True) ]
#        print(' '.join(mv_out_file))
#        subprocess.call(mv_out_file)
#        subprocess.call(['mv', 'auto_final.in', 'input.in'])
#
#    def next_file(self, pattern, increment):
#        count = self.count
#        if increment: # TODO: this is a band-aid fix
#            self.count += 1
#        return pattern + '.' + str(count)
#
#    @print_args
#    def job_finished(self):
# TODO: to be completed

#class BGQAutorunner(Autorunner2):

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

#!/usr/bin/env python
# autorunning qmcpack on bgq servers

import autorunner
from autorunner import Autorunner
import argparse
import os
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('cores')
parser.add_argument('realcplx')
parser.add_argument('--mixed-precision', '-mp', action='store_true')
parser.add_argument('--nsample', '-n', type=int, required=True)
parser.add_argument('--interval', '-i', type=int, required=True)
parsed_args = parser.parse_args()

core = parsed_args.cores
realcp = parsed_args.realcplx
prec = 'mp' if parsed_args.mixed_precision else ''

OLD_THRESHOLD = 80000000

@autorunner.latest(pattern='*.cobaltlog')
#@autorunner.not_old(threshold=OLD_THRESHOLD)
@autorunner.not_old()
@autorunner.print_args
def _job_finished(*args, **kwargs):
    return autorunner.done_cobaltlog(*args, **kwargs)

@autorunner.dmc_dat(start=5)
@autorunner.print_args
def _enough_samples(*args, **kwargs):
    return autorunner.check_nsample(target=parsed_args.nsample, *args, **kwargs)

@autorunner.print_args
def _submit(inputs, core, realcp, prec):
    with open('template', 'w') as fh:
        fh.write('\n'.join(sorted(inputs)))
        fh.write('\n')
    qsub = [ 'bgq_auto.sh', core, realcp, prec ]
    subprocess.call(qsub)

def _sensor():
    if (_enough_samples() and _job_finished()):
        return True
    else:
        return False

@autorunner.timestamp
def _actuator():
    cont_files = sorted([x for x in os.listdir('.') if 'cont.xml' in x ],
            key=lambda x: os.stat(x).st_mtime)
    last_series = re.search(r'\.s[0-9]+\.', cont_files[-1]).group()
    _submit([ x for x in cont_files if last_series in x ], core, realcp, prec)

auto = Autorunner(sensor=_sensor, actuator=_actuator)
_actuator()
auto.run(interval=parsed_args.interval)

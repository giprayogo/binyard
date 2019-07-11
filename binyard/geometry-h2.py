#!/usr/bin/env python

from binyard.fileio import parse
from numpy import array
from numpy import isclose
from numpy.linalg import norm
import sys

b2a = 0.529177210903
for filename in sys.argv[1:]:
    pwx = parse('pwx', filename)
    ap = pwx['atomic_positions']
    assert(ap['options'] == 'crystal')
    cpv = array(pwx['cell_parameters']['value'])
    # temporarily disable to fix ads_struct_* in H2
    #for axis in cpv:
        #assert isclose(norm(axis), 1.)
    apv = ap['value']
    apvn = array([ x[1:4] for x in apv ], dtype='float')
    celldm = float(pwx['celldm(1)']['value'])
    # so that they are in anstrom
    print('{} {}'.format(filename, b2a * celldm * norm(apvn[1]-apvn[0])))

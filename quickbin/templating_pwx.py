#!/usr/bin/env python
# Script to copy geometry from for example, cif2cell generated pw.x
# partial input file into a template file containing all simulation parameters
# TODO: tidy up and merge into quickbin

import os
import numpy as np
import sys
import shutil
import glob

import m_module.fileio as fileio

np.set_printoptions(precision=15)
script = os.path.basename(__file__)

# read input files
try:
    template = sys.argv[1]
    structure = sys.argv[2]
except IndexError:
    print(script+": Usage: {} TEMPLATE_INPUT STRUCTURE_FILE".format(sys.argv[0]))
    exit()

# force availability of job submit files
try:
    username = open('UserName', 'r')
    print(username.readlines())
    username.close()
except IOError:
    print(script+": UserName: No such file")
    exit()
try:
    jobname = open('JobName', 'r')
    print(jobname.readlines())
    jobname.close()
except IOError:
    print(script+": JobName: No such file")
    exit()
try:
    pp = open('Si.bfd.upf', 'r')
    pp.close()
except IOError:
    print(script+": Si.bfd.upf: No such file")
    exit()
try:
    pp = open('C.BFD.upf', 'r')
    pp.close()
except IOError:
    print(script+": C.bfd.upf: No such file")
    exit()
try:
    pp = open('H.BFD.upf', 'r')
    pp.close()
except IOError:
    print(script+": H.bfd.upf: No such file")
    exit()

pwi = fileio.parse_pwx(template)
pws = fileio.parse_pwx(structure)
# copy structure file parameters to template
pwi['celldm(1)']['value'] = pws['celldm(1)']['value']
pwi['nat']['value'] = pws['nat']['value']
pwi['ntyp']['value'] = pws['ntyp']['value']
pwi['cell_parameters']['value'] = pws['cell_parameters']['value']
pwi['cell_parameters']['options'] = pws['cell_parameters']['options']
pwi['atomic_positions']['value'] = pws['atomic_positions']['value']
pwi['atomic_positions']['options'] = pws['atomic_positions']['options']
pwi['atomic_species'] = pws['atomic_species']

print(fileio.tostring_pwx(pwi))

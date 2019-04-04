#!/usr/bin/env python
# Script to copy geometry from for example, cif2cell generated pw.x
# partial input file into a template file containing all simulation parameters
# TODO: tidy up and merge into quickbin

import os
import numpy as np
import sys
import shutil
import glob

import argparse

import m_module.fileio as fileio

np.set_printoptions(precision=15)
script = os.path.basename(__file__)

# read input files
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--template-file', required=True,
        help='template pw.x input file with all simulation parameters')
parser.add_argument('-s', '--structure-file', required=True,
        help='pw.x input file with final structure')

parsed = parser.parse_args()
template = parsed.template_file
structure = parsed.structure_file

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
#pwi['atomic_species'] = pws['atomic_species']

print(fileio.tostring_pwx(pwi))

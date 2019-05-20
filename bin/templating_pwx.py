#!/usr/bin/env python
# Merge geometry and run parrameters from 2 different pw.x input files

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

args = parser.parse_args()

template = fileio.parse_pwx(args.template_file)
structure = fileio.parse_pwx(args.structure_file)
template['celldm(1)']['value'] = structure['celldm(1)']['value']
template['nat']['value'] = structure['nat']['value']
template['ntyp']['value'] = structure['ntyp']['value']
template['cell_parameters'] = structure['cell_parameters']
template['atomic_positions'] = structure['atomic_positions']
template['atomic_species'] =structure['atomic_species']

print(fileio.tostring_pwx(template))

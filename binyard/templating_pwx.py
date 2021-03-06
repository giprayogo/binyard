#!/usr/bin/env python
# Merge geometry and run parrameters from 2 different pw.x input files

import argparse
import fileio

# read input files
parser = argparse.ArgumentParser()
parser.add_argument('-t', '--template-file', required=True,
        help='template pw.x input file with all simulation parameters')
parser.add_argument('-s', '--structure-file', required=True,
        help='pw.x input file with final structure')

args = parser.parse_args()

template = fileio.parse('pwx', args.template_file)
structure = fileio.parse('pwx', args.structure_file)
template['celldm(1)']['value'] = structure['celldm(1)']['value']
template['nat']['value'] = structure['nat']['value']
template['ntyp']['value'] = structure['ntyp']['value']
template['cell_parameters'] = structure['cell_parameters']
template['atomic_positions'] = structure['atomic_positions']
# some structure files are BAD
#template['atomic_species'] = structure['atomic_species']

print(fileio.tostring_pwx(template))

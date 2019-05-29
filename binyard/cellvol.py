#!/usr/bin/env python
# calculate PRIMITIVE cell volume
# TODO: multiple units

import fileio
import argparse
import xml.etree.ElementTree as ET
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('input', nargs='+')
args = parser.parse_args()

input_files = args.input

bohr2angstrom = 0.529177210903

#TODO: units
# TODO: proper file type detection
def volume(filename):
    volumer = get_volumer(filename)
    return volumer(filename)

def get_volumer(filename):
    if '.xml' in filename:
        return qmcpack_volumer
    elif '.in' in filename:
        return qe_volumer
    elif '.cif' in filename:
        return cif_volumer
    else:
        raise ValueError('unsupported format')


def cif_volumer(filename):
    with open(filename, 'r') as fh:
        for line in fh:
            if '_cell_volume' in line:
                cell_volume = float(line.split()[1])
    return cell_volume

def qmcpack_volumer(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    lattice_xml = fileio.get_xmlelement_from_obj(root,
            'qmcsystem.simulationcell.parameter[0]')
    tiling_matrix = np.reshape(np.array(fileio.get_xmlelement_from_obj(root,
            'wavefunction.determinantset.tilematrix').split(), dtype='float_'), (3,3))
    supercell = int(round(np.abs(np.linalg.det(tiling_matrix))))
    # TODO: simplify
    lattice = np.array([ list(map(float, x.split()))
            for x in filter(None, lattice_xml.text.split('\n')) ])
    volume = np.dot(lattice[0], np.cross(lattice[1], lattice[2])) / supercell
    #print(volume) #in bohr3
    return volume
    #volume_a3 = volume * ( bohr2angstrom ** 3 )
    #return volume_a3

def qe_volumer(filename):
    pwi = fileio.parse('pwx', filename)
    lattice = np.array([ list(map(float, x))
            for x in pwi['cell_parameters']['value'] ])
    #TODO: proper conversion between units
    assert pwi['cell_parameters']['options'].lower() == 'alat' or\
            pwi['cell_parameters']['options'] == ''
    celldm = np.array(float(pwi['celldm(1)']['value']))
    volume = np.abs(np.dot(lattice[0], np.cross(lattice[1], lattice[2]))) * ( celldm ** 3 )
    return volume
    #volume_a3 = volume * ( bohr2angstrom ** 3 )
    #return volume_a3

for input_file in input_files:
    print(' '.join([input_file, str(volume(input_file))]))

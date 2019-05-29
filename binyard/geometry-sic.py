#!/usr/bin/env python

import fileio

import argparse
import numpy as np
import os

np.set_printoptions(precision=15) # match QE printed precision

def normalize(vector):
    return vector / np.linalg.norm(vector)

parser = argparse.ArgumentParser()
parser.add_argument('pwx_input_file')
parser.add_argument('--table', '-t', action='store_true')
parser.add_argument('--zigzag', '-z', action='store_true')
parser.add_argument('--no-header', '-n', action='store_true')
parser.add_argument('--out-file', '-o', required=True)
args = parser.parse_args()
pwi = fileio.parse_pwx(args.pwx_input_file)

# pre-determined assertions
# make sure that vacuum is at x and y axes
assert np.linalg.norm(pwi['cell_parameters']['value'][0]) == np.linalg.norm(pwi['cell_parameters']['value'][1])
# only bother crystal and alat units
unit = pwi['atomic_positions']['options']
assert unit == 'crystal' or unit == 'alat'

# makeshift adjustment
if not args.zigzag:
    P_BOND_ANGLE = 90
    D_BOND_ANGLE = 30
else:
    P_BOND_ANGLE = 0
    D_BOND_ANGLE = 60

# unit conversions
# try not to convert to bohr/angstom until the very last
bohr2angstrom = 0.529177249
alat2angstrom = float(pwi['celldm(1)']['value']) * bohr2angstrom
# matrices for conversion to/from crystal and cartesian units (in alat)
M = (np.array(pwi['cell_parameters']['value'], dtype='f8'))
Ma = M * alat2angstrom
M_inv = np.linalg.inv(M)
Mai = np.linalg.inv(Ma)

def crystal2alat(positions):
    return [ np.matmul(M, pos) for pos in positions ]
def alat2crystal(positions):
    return [ np.matmul(M_inv, pos) for pos in positions ]
def toalatifcrystal(positions):
    if pwi['atomic_positions']['options'] == 'crystal':
        return crystal2alat(positions)
    return positions

# split species array and position array to simplify codes (like qmcpack)
atom_species_array = np.array( [ single_atom[0]
    for single_atom in pwi['atomic_positions']['value'] ] , dtype='S')
atom_position_array = toalatifcrystal(np.array( [ single_atom[1:]
    for single_atom in pwi['atomic_positions']['value'] ] , dtype='f8'))
sic_atoms = [ v for i, v in enumerate(atom_position_array)
        if atom_species_array[i] == b'Si' or atom_species_array[i] == b'C' ]
si_atoms = [ v for i, v in enumerate(atom_position_array)
        if atom_species_array[i] == b'Si' ]
c_atoms = [ v for i, v in enumerate(atom_position_array)
        if atom_species_array[i] == b'C' ]

sic_center = sum(sic_atoms) / len(sic_atoms)

def degangle(v1, v2):
    assert len(v1) == len(v2) == 3
    assert np.isclose(np.linalg.norm(v1), 1.0) and np.isclose(np.linalg.norm(v2), 1.0)
    return min(np.rad2deg(np.arccos(np.dot(v1, v2))), np.rad2deg(np.arccos(np.dot(v1, -v2))))

# x-y radius
def mean_radii(position_list):
    #return sum([ np.linalg.norm(x[:-1] - sic_center[:-1]) for x in position_list ]) / len(position_list)
    return np.array([ np.linalg.norm(x[:-1] - sic_center[:-1]) for x in position_list ]).mean()

def var_radii(position_list):
    return np.array([ np.linalg.norm(x[:-1] - sic_center[:-1]) for x in position_list ]).var()


bonds = [ ai-aj for i, ai in enumerate(sic_atoms) for j, aj in enumerate(sic_atoms) if j > i ]
bonds_r = list(map(lambda y: np.linalg.norm(y) * alat2angstrom,
        filter(lambda x: np.linalg.norm(x) * alat2angstrom < 2.0, bonds)))
p_bonds_r = list(map(lambda y: np.linalg.norm(y) * alat2angstrom,
        filter(lambda x: np.linalg.norm(x) * alat2angstrom < 2.0
            and np.isclose(degangle(normalize(x), np.array([0, 0, 1])), P_BOND_ANGLE, atol=10.0),
                bonds)))
d_bonds_r = list(map(lambda y: np.linalg.norm(y) * alat2angstrom,
        filter(lambda x: np.linalg.norm(x) * alat2angstrom < 2.0
        and np.isclose(degangle(normalize(x), np.array([0, 0, 1])), D_BOND_ANGLE, atol=10.0),
            bonds)))

si_r_ave = mean_radii(si_atoms) * alat2angstrom
c_r_ave = mean_radii(c_atoms) * alat2angstrom
buckling = si_r_ave - c_r_ave
si_r_sigma = var_radii(si_atoms) * alat2angstrom
c_r_sigma = var_radii(c_atoms) * alat2angstrom

def get_energy(out_file):
    with open(out_file, 'r') as fh:
        return [ line for line in fh.readlines() if '!' in line ][-1].split()[4]

def average(x):
    return sum(x) / len(x)

if not args.table:
    print("Average Si-C bonds length (Å): {}".format(average(bonds_r)))
    print("Average P Si-C bonds length (Å): {}".format(average(p_bonds_r)))
    print("Average D Si-C bonds length (Å): {}".format(average(d_bonds_r)))
    print("SiCNT center coordinate (alat): {}".format(sic_center))
    print("SiCNT center coordinate (Å): {}".format(sic_center * alat2angstrom))
    print("average Si x-y radii (Å): {}".format(si_r_ave))
    print("average C x-y radii (Å): {}".format(c_r_ave))
    print("---------------------------")
else:
    if not args.no_header:
        print('#DIR bond lengths              radius            E')
        print('#    all  para/perp  diagonal  Si  Si_v  C  C_v')
    print(' '.join(map(str,
        [os.getcwd(), average(bonds_r), average(p_bonds_r), average(d_bonds_r), si_r_ave, si_r_sigma, c_r_ave, c_r_sigma, buckling, get_energy(args.out_file)])))

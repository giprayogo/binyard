#!/usr/bin/env python

import m_module.fileio as fileio

import argparse
import numpy as np

np.set_printoptions(precision=15) # match QE printed precision

RING_SIZE = {'hollow': 6, 'bridge': 2, 'top': 1}
HALF_RING_SIZE = {'hollow': 4, 'bridge': 2, 'top': 1}

def normalize(vector):
    return vector / np.linalg.norm(vector)

parser = argparse.ArgumentParser()
parser.add_argument('pwx_input_file')
parser.add_argument('--pwx-site-file', '-f', type=str, help='Used when optimized geometry shifted far from the initial site')
parser.add_argument('--site', '-s', type=str, required=True, choices=['hollow', 'bridge', 'top'], help='Adsorption site')
parser.add_argument('--table', '-t', action='store_true', help='Print in mergeable format')
#parser.add_argument('--out', action='store_true', required=True) # read output file also; not implemented
args = parser.parse_args()
pwi = fileio.parse_pwx(args.pwx_input_file)

# pre-determined assertions
# make sure that vacuum is at x and y axes
assert np.linalg.norm(pwi['cell_parameters']['value'][0]) == np.linalg.norm(pwi['cell_parameters']['value'][1])
# only bother crystal and alat units
unit = pwi['atomic_positions']['options']
assert unit == 'crystal' or unit == 'alat'

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


atom_species_array = np.array( [ single_atom[0]
    for single_atom in pwi['atomic_positions']['value'] ] , dtype='S')
atom_position_array = toalatifcrystal(np.array( [ single_atom[1:]
    for single_atom in pwi['atomic_positions']['value'] ] , dtype='f8'))


h_atoms = [ v for i, v in enumerate(atom_position_array) if atom_species_array[i] == b'H' ]
assert len(h_atoms) != 0
sic_atoms = [ v for i, v in enumerate(atom_position_array)
        if atom_species_array[i] == b'Si' or atom_species_array[i] == b'C' ]
si_atoms = [ v for i, v in enumerate(atom_position_array)
        if atom_species_array[i] == b'Si' ]
c_atoms = [ v for i, v in enumerate(atom_position_array)
        if atom_species_array[i] == b'C' ]

h_center = sum(h_atoms) / len(h_atoms)
sic_center = sum(sic_atoms) / len(sic_atoms)
si_center = sum(si_atoms) / len(si_atoms)
c_center = sum(c_atoms) / len(c_atoms)

#TODO; tidy up
if args.pwx_site_file:
    original_pwi = fileio.parse_pwx(args.pwx_site_file)
    original_atom_species_array = np.array( [ single_atom[0]
        for single_atom in original_pwi['atomic_positions']['value'] ] , dtype='S')
    original_atom_position_array = toalatifcrystal(np.array( [ single_atom[1:]
        for single_atom in original_pwi['atomic_positions']['value'] ] , dtype='f8'))
    original_h_atoms = [ v for i, v in enumerate(original_atom_position_array) if original_atom_species_array[i] == b'H' ]
    assert len(h_atoms) != 0
    original_h_center = sum(original_h_atoms) / len(original_h_atoms)

# finding H center's nearest neighbors list
# the goal is to find the Si-C hexagonal 'ring'
# use manual switch for hollow/top/bridge
def nn(center, position_list, n):
    def sort_by_distance(position):
        return np.linalg.norm(position - center)
    return sorted(position_list, key=sort_by_distance) [:n]

# copy atoms close to the cell boundaries
def pbc_copy(position_list):
    def different(a, b):
        if np.isclose(a, b).all():
            return False
        return True

    copies_list = []
    # evaluate all x, y, z (although only z will be possible since x-y are vacuum)
    for atom in position_list:
        copy = np.array([ x if not np.isclose(x, 0.0, atol=0.05) else x+1 for x in atom ])
        if different(atom, copy): # see if it was copied
            copies_list.append(copy)
    position_list.extend(copies_list)
    return position_list

if args.pwx_site_file:
    sic_ring = pbc_copy(nn(original_h_center, sic_atoms, HALF_RING_SIZE[args.site] ))
else:
    sic_ring = pbc_copy(nn(h_center, sic_atoms, HALF_RING_SIZE[args.site] ))
#print(sic_ring)
assert len(sic_ring) == RING_SIZE[args.site] # make sure it properly detects all Si-C ring
sic_ring_center = sum(sic_ring) / len(sic_ring)
sic_ring_r = sic_ring_center[:-1] - sic_center[:-1]
sic_ring_r_norm = normalize(sic_ring_r)


#----------------------------------------------
# adsorption geometry calculations
h_sic_axis = normalize(h_center[:-1] - sic_center[:-1])
tilt = np.arccos(np.dot(h_sic_axis, np.array([-1.0, 0.0]))) #in radian
tilt_matrix = np.array([ [np.cos(tilt),-np.sin(tilt),0.0], [np.sin(tilt),np.cos(tilt),0.0], [0.0,0.0,1.0]])

# cartesian x,y,z axes, tilted relative to the adsorbed hydrogen center
# z is unecessary since 
tilted_x = np.matmul( np.array([1.0,0.0,0.0]), tilt_matrix) #the surface normal
tilted_y = np.matmul( np.array([0.0,1.0,0.0]), tilt_matrix) # the surface perpendicular
tilted_z = np.matmul( np.array([0.0,0.0,1.0]), tilt_matrix)

def degangle(v1, v2):
    return min(np.rad2deg(np.arccos(np.dot(v1, v2))), np.rad2deg(np.arccos(np.dot(v1, -v2))))

# vector between H atoms
h_axis = normalize(h_atoms[0] - h_atoms[1]) # in alat; careful for z shift
h_surface_angle = degangle(h_axis, tilted_y)
h_twist_angle = np.rad2deg(np.arccos(np.dot(h_axis, tilted_z)))
h_ring_angle = np.rad2deg(np.arccos(np.dot(h_sic_axis, sic_ring_r_norm)))

# x-y radius
def get_mean_radii(position_list):
    #mean = sum(position_list[:-1]) / len(position_list) 
    return sum([ np.linalg.norm(x[:-1] - sic_center[:-1]) for x in position_list ]) / len(position_list)

si_r_ave = get_mean_radii(si_atoms)
c_r_ave = get_mean_radii(c_atoms)

if not args.table:
    # coordinates for recheck
    print("SiCNT center coordinate (Å): {}".format(sic_center * alat2angstrom))
    print("H center coordinate (Å): {}".format(h_center * alat2angstrom))
    print("Si-C adsorption site: {}, nn: {}".format(args.site, [ x * alat2angstrom for x in sic_ring ]))
    # radial lengths
    print("H center to SiCNT center x-y distance (Å): {}".format(
        np.linalg.norm((h_center[:-1] - sic_center[:-1])) * alat2angstrom))
    print("average Si x-y radii (Å): {}".format(si_r_ave * alat2angstrom))
    print("average C x-y radii (Å): {}".format(c_r_ave *alat2angstrom))
    print("---------------------------")
    h_center_r = np.linalg.norm(h_center[:-1] - sic_center[:-1])
    print("H2 geometric center distance to NT surface [Å]: {}".format(
        alat2angstrom * (h_center_r - si_r_ave) if si_r_ave > c_r_ave else alat2angstrom * (h_center_r - c_r_ave)))
    # angles
    print("H2 to surface normal angle [deg]: {}".format(h_surface_angle))
    print("H2 to cylinder axis angle [deg]: {}".format(h_twist_angle))
    print("H2 centroid to site center shift angle [deg]: {}".format(h_ring_angle))
else:
    # TODO: fix copy pastes
    h_center_r = np.linalg.norm(h_center[:-1] - sic_center[:-1])
    #print('# H2-SiCNT center ; Si_R           ; C_R           ; H2-SiCNT surface ; H-S surface angle ; H-S z-angle       ; H-S ads. angle')
    #print("{} {} {} {} {} {} {}".format(
    #    h_center_r * alat2angstrom,
    #    si_r_ave * alat2angstrom,
    #    c_r_ave * alat2angstrom,
    #    alat2angstrom * (h_center_r - si_r_ave) if si_r_ave > c_r_ave else alat2angstrom * (h_center_r - c_r_ave),
    #    h_surface_angle,
    #    h_twist_angle,
    #    h_ring_angle))
    print('#H2-SiCNT surface ; H-S surface angle ; H-S z-angle       ; H-S ads. angle')
    print("{} {} {} {}".format(
        alat2angstrom * (h_center_r - si_r_ave) if si_r_ave > c_r_ave else alat2angstrom * (h_center_r - c_r_ave),
        h_surface_angle,
        h_twist_angle,
        h_ring_angle,
        energy))

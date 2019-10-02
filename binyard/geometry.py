#!/usr/bin/env python

from fileio import parse

import argparse
import numpy as np
from numpy import array
from numpy.linalg import inv
from numpy.linalg import norm
from numpy import dot
from numpy import matmul
import os

np.set_printoptions(precision=15) # match QE printed precision

RING_SIZE = {'hollow': 6, 'bridge': 2, 'top': 1}
HALF_RING_SIZE = {'hollow': 4, 'bridge': 2, 'top': 1}

def normalize(vector):
    return vector / norm(vector)

def project(v, n):
    nb = normalize(n)
    return v - nb*(dot(n,v) / norm(n))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pwx_input_file')
    parser.add_argument('--pwx-site-file', '-f',
            required=True,
            type=str,
            help='Reference initial geometry. Pre-optimization')
    parser.add_argument('--site', '-s',
            type=str, required=True,
            choices=['hollow', 'bridge', 'top'],
            help='Adsorption site')
    parser.add_argument('--table', '-t', action='store_true',
            help='Print in mergeable format')
    parser.add_argument('--out-file', '-o', required=True)
    #parser.add_argument('--bare', '-b', required=True)
    parser.add_argument('--no-header', '-n', action='store_true')
    args = parser.parse_args()
    pwi = parse('pwx', args.pwx_input_file)

    # pre-determined assertions
    # make sure that vacuum is at x and y axes
    assert np.linalg.norm(pwi['cell_parameters']['value'][0]) == np.linalg.norm(pwi['cell_parameters']['value'][1])
    # only bother crystal and alat units
    unit = pwi['atomic_positions']['options']
    assert unit == 'crystal' or unit == 'alat'

    # unit conversions
    # try not to convert to bohr/angstom until the very last
    bohr2angstrom = 0.529177249
    celldm = float(pwi['celldm(1)']['value'])
    alat2angstrom = celldm * bohr2angstrom
    # matrices for conversion to/from crystal and cartesian units (in alat)
    M = (np.array(pwi['cell_parameters']['value'], dtype='f8'))
    Ma = M * alat2angstrom
    M_inv = (M)
    Mai = inv(Ma)

    def crystal2alat(positions):
        return [ matmul(M, pos) for pos in positions ]
    def alat2crystal(positions):
        return [ matmul(inv(M), pos) for pos in positions ]
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
    # this part is only used to calculate -shift- from the original location
    original_pwi = parse('pwx', args.pwx_site_file)
    original_atom_species_array = np.array( [ single_atom[0]
        for single_atom in original_pwi['atomic_positions']['value'] ] , dtype='S')
    original_atom_position_array = toalatifcrystal(np.array( [ single_atom[1:]
        for single_atom in original_pwi['atomic_positions']['value'] ] , dtype='f8'))
    original_h_atoms = [ v for i, v in enumerate(original_atom_position_array) if original_atom_species_array[i] == b'H' ]
    original_sic_atoms  = [ v for i, v in enumerate(original_atom_position_array) if original_atom_species_array[i] == b'Si' or original_atom_species_array[i] == b'C' ]
    assert len(h_atoms) != 0
    original_h_center = sum(original_h_atoms) / len(original_h_atoms)
    original_sic_center = sum(original_sic_atoms) / len(original_sic_atoms)

    # yeah; I know it is a one-liner
    def relative(r, r0):
        return r-r0
    metric = norm(relative(h_center, sic_center) - relative(original_h_center, original_sic_center))
    #---------start of geometrical section---------
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

    sic_ring = pbc_copy(nn(original_h_center, sic_atoms, HALF_RING_SIZE[args.site] ))
    #print(sic_ring)
    assert len(sic_ring) == RING_SIZE[args.site] # make sure it properly detects all Si-C ring
    sic_ring_center = sum(sic_ring) / len(sic_ring)
    sic_ring_r = sic_ring_center[:-1] - sic_center[:-1]
    sic_ring_r_norm = normalize(sic_ring_r)

    #----------------------------------------------
    # adsorption geometry calculations
    def getRmatrix(angle, axis):
        assert len(axis) ==3
        # angle in rad
        return np.cos(angle)*np.identity(3) + np.sin(angle)*np.array([
            [       0, -axis[2],  axis[1]],
            [ axis[2],        0, -axis[0]],
            [-axis[1],  axis[0],        0]
            ,]) + (1 - np.cos(angle))*np.outer(axis, axis)

    h_sic_axis = normalize(h_center[:-1] - sic_center[:-1])
    #print(alat2crystal([sic_center]))
    # negative here is -very- important, because of the quadrant where I put the H2.
    # ideally it should self-identify which one to be used but then I don't want to spend the time
    tilt = np.arccos(np.dot(h_sic_axis, np.array([-1.0, 0.0]))) #in radian
    #tilt_matrix = np.array([ [np.cos(tilt),-np.sin(tilt),0.0], [np.sin(tilt),np.cos(tilt),0.0], [0.0,0.0,1.0]])
    tilt_matrix = getRmatrix(tilt, [0.0, 0.0, 1.0])
    #print(tilt_matrix)

    # cartesian x,y,z axes, tilted relative to the adsorbed hydrogen center
    # z is unecessary since
    tilted_x = np.matmul( np.array([1.0,0.0,0.0]), tilt_matrix) #the surface normal
    tilted_y = np.matmul( np.array([0.0,1.0,0.0]), tilt_matrix) # the surface perpendicular
    tilted_z = np.matmul( np.array([0.0,0.0,1.0]), tilt_matrix)
    #print(tilt_matrix)

    def min_angle(v1, v2):
        return min(np.rad2deg(np.arccos(np.dot(v1, v2))), np.rad2deg(np.arccos(np.dot(v1, -v2))))

    # vector between H atoms
    h_axis = normalize(h_atoms[0] - h_atoms[1]) # in alat; careful for z shift

    # relative to surface normal (negative tilted x)
    h_surface_angle = min_angle(h_axis, -tilted_x)
    # for the twist, project h first agains the surface
    h_h = norm(h_atoms[0]-h_atoms[1])
    h_proj = project(h_axis, -tilted_x)
    #print(dot(h_proj, -tilted_x))
    #print(h_atoms[0])
    #print(alat2crystal([h_center]))
    #print(alat2crystal([h_center+2*h_h*tilted_z]))
    #print(alat2crystal([h_center+3*h_h*h_proj]))
    #print(np.rad2deg(np.arccos(np.dot(h_proj, tilted_y))))
    #print(np.rad2deg(np.arccos(np.dot(h_proj, tilted_z))))
    h_twist_angle = min_angle(normalize(h_proj), tilted_z)

    # x-y radius
    def mean_radii(positions, center):
        #mean = sum(position_list[:-1]) / len(position_list)
        return sum([ norm(x[:-1] - center[:-1]) for x in positions]) / len(positions)

    si_r_ave = mean_radii(si_atoms, sic_center)
    c_r_ave = mean_radii(c_atoms, sic_center)

    def get_energy(out_file):
        with open(out_file, 'r') as fh:
            return [ line for line in fh if '!' in line ][-1].split()[4]

    #TODOL can these be shortened?
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
        print("H2 shift from original location (Å) {}".format(metric * alat2angstrom))
        print("SCF energy [Ry]: {}".format(h_twist_angle))
    else:
        # TODO: fix copy pastes
        h_center_r = np.linalg.norm(h_center[:-1] - sic_center[:-1])
        if not args.no_header:
            print('#cwd; surface distance; surface angle; axis angle; shift; SCF energy')

        print(*[
           os.getcwd(),
           alat2angstrom * (h_center_r - si_r_ave) if si_r_ave > c_r_ave else alat2angstrom * (h_center_r - c_r_ave),
           h_surface_angle,
           h_twist_angle,
           metric * alat2angstrom,
           get_energy(args.out_file) ])

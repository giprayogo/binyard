#!/usr/bin/env python

import sys

import m_module.fileio as fileio
import numpy as np
#import math

np.set_printoptions(precision=15)

input_file = None
try:
    input_file = sys.argv[1]
except IndexError:
    print("Usage: "+sys.argv[0]+" PW.X_INPUT_FILE")
    exit()
pwi = fileio.parse_pwx(input_file)

bohr2angstrom = 0.529177249
#alat = float(pwi['celldm(1)']['value'], dtype='float') * bohr2angstrom
alat = float(pwi['celldm(1)']['value']) * bohr2angstrom

M = (np.array(pwi['cell_parameters']['value'], dtype='f8'))
Ma = M * alat
Mi = np.linalg.inv(M)
Mai = np.linalg.inv(Ma)

atomic_position = np.array( [ tuple(single_atom)[:4] # discard fixed atom position
    for single_atom in pwi['atomic_positions']['value'] ],
        dtype='S3,f8,f8,f8')

# finding centers of each fragment
s = np.array([0.0,0.0,0.0])
h = np.array([0.0,0.0,0.0])
s_n = 0
h_n = 0
for a in atomic_position:
    #print(list(a)[1:])
    if not (a[0].decode("utf-8") == 'H'):
        s += list(a)[1:]
        s_n += 1
    else:
        h += list(a)[1:]
        h_n += 1
# convert to Angstrom
center = np.matmul(s/s_n, Ma)
h_center = np.matmul(h/h_n, Ma)

# finding H center's nearest neighbors
# TODO: generalize
def nearest(element, num):
    nearest = []
    for a in atomic_position:
        a_element = a[0].decode("utf-8")
        if not (a_element == 'H') and a_element == element:
            nearest.append(a)
    def sort_by_distance(atom):
        return np.linalg.norm( np.matmul(list(atom)[1:], Ma) - h_center )
    return sorted(nearest, key=sort_by_distance) [:num]

def periodic_bound(atom_list):
    # add atom copies for near boundaries
    def different(just_position):
        for atom in atom_list:
            position = np.array(list(atom)[1:])
            if np.isclose(np.linalg.norm(position - np.array(just_position)), 0.0):
                return False
        return True

    new_atom_list = np.empty(0, dtype='S3,f8,f8,f8')
    for atom in atom_list:
        element = list(atom)[0]
        dupli = [ i if not np.isclose(i, 0.0) else i+1 for i in list(atom)[1:]  ] # assumed alat
        if different(dupli):
            dupli.insert(0, element)
            new_atom_list = np.append(new_atom_list, np.array( tuple(dupli), dtype='S3,f8,f8,f8'))
    return np.append(atom_list, new_atom_list)

atomic_position = np.array( [ tuple(single_atom)[:4] # discard fixed atom position
    for single_atom in pwi['atomic_positions']['value'] ],
        dtype='S3,f8,f8,f8')

C_ring = periodic_bound(nearest('C', 2))
Si_ring = periodic_bound(nearest('Si', 2))
the_ring = np.append(C_ring, Si_ring)

centroid = np.array([0.0,0.0,0.0])
for atom in the_ring:
    #print(atom)
    centroid += np.array(list(atom)[1:])
centroid /= len(the_ring) # in alat

# important angles
the_ax = (h_center[:-1] - center[:-1])
the_ax_norm = the_ax / np.linalg.norm(the_ax)
tilt = np.arccos(np.dot(the_ax_norm, np.array([-1.0, 0.0]))) #in radian
tilt_matrix = np.array([ [np.cos(tilt),-np.sin(tilt),0.0], [np.sin(tilt),np.cos(tilt),0.0], [0.0,0.0,1.0]])

# will do tilt -> cart; invert for cart -> tilt
adsorption_axes = np.matmul(np.array([[1.0,0.0,0.0], [0.0,1.0,0.0], [0.0,0.0,1.0]]), tilt_matrix)

tilted_x = np.matmul( np.array([1.0,0.0,0.0]), tilt_matrix) #the surface normal
tilted_y = np.matmul( np.array([0.0,1.0,0.0]), tilt_matrix) # the surface perpendicular
tilted_z = np.matmul( np.array([0.0,0.0,1.0]), tilt_matrix)

# get "direction" of the H
Hs = [ atom for atom in atomic_position if atom[0].decode("utf-8") == 'H' ]
h_ax = np.array(list(Hs[0])[1:]) - np.array(list(Hs[1])[1:]) # in alat; careful for z shift
h_ax_carte = np.matmul(h_ax, Ma) # now in angstrom
h_ax_carte_norm = h_ax_carte / np.linalg.norm(h_ax_carte)

#print(np.rad2deg(np.arccos(np.dot(h_ax_carte_norm, tilted_y))))
h_surface_angle = np.rad2deg(np.arccos(np.dot(h_ax_carte_norm, tilted_x)))
h_twist_angle = np.rad2deg(np.arccos(np.dot(h_ax_carte_norm, tilted_z))) #- 90.0
#print(np.rad2deg(np.arccos(np.dot(h_ax_carte_norm, tilted_z))))

center_alat = np.matmul(center, np.linalg.inv(Ma)) # to alat
center_shifted = np.append(center_alat[:-1], 0.5) # still in alat
centroid_radial_out = np.matmul(centroid, Ma) - np.matmul(center_shifted, Ma) #carte (Å)
centroid_radial_out_norm = centroid_radial_out / np.linalg.norm(centroid_radial_out)
h_radial_out = h_center - np.matmul(center_shifted, Ma) # already cartesian angstrom
h_radial_out_norm = h_radial_out / np.linalg.norm(h_radial_out)
h_centroid_angle = np.rad2deg(np.arccos(np.dot(centroid_radial_out_norm, h_radial_out_norm)))

# useful for testing tilt
#print(np.matmul(np.array([0.3,0.0,0.0]), adsorption_axes) + np.array([0.5,0.5,0.0]) )
#print(np.matmul(np.array([-0.3,0.0,0.0]), adsorption_axes)+ np.array([0.5,0.5,0.0]) )
#print(np.matmul(np.array([0.0,0.3,0.0]), adsorption_axes) + np.array([0.5,0.5,0.0]) )
#print(np.matmul(np.array([0.0,-0.3,0.0]), adsorption_axes)+ np.array([0.5,0.5,0.0]) )

# NT radius calculations
ssi = 0; nsi = 0
sc = 0; nc = 0
for a in atomic_position:
    aa = np.matmul(list(a)[1:], Ma)
    #print(a[0].decode("utf-8"), np.linalg.norm(list(a)[1:] - center))
    r = np.linalg.norm(aa[:-1] - center[:-1])
  #  print(a[0].decode("utf-8"), r)
    if (a[0].decode("utf-8") == 'Si'):
        ssi += r
        nsi += 1
    elif (a[0].decode("utf-8") == 'C'):
        sc += r
        nc += 1

si_r_ave = ssi/nsi
c_r_ave = sc/nc
h_center_r = np.linalg.norm(h_center[:-1] - center[:-1])
print("center (Å): {}".format(center))
print("H center (Å): {}".format(h_center))
print("H center dist (Å): {}".format(h_center_r))
print("average Si rad (Å): {}".format(si_r_ave))
print("average C rad (Å): {}".format(c_r_ave))
print("---------------------------")
print("H center - NT surface distance [Å]: {}".format(
    (h_center_r - si_r_ave) if si_r_ave > c_r_ave else (h_center_r - c_r_ave)))
print("H-NT surface angle [deg]: {}".format(h_surface_angle))
print("H-NT perpendicular twist angle [deg]: {}".format(h_twist_angle))
print("H-centroid shift angle [deg]: {}".format(h_centroid_angle))

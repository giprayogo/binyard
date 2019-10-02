#!/usr/bin/env python
# Note: does not use fancy processings;
# only valid for same-grid calculations

import numpy as np
from sys import argv
from collections import defaultdict


def read_charge(density_file):
    cube = defaultdict(list)
    with open(density_file, 'r') as xx:
        # hand-handled
        numerical_data = xx.readlines()[2:]
    nat = int(numerical_data[0].split()[0])
    nx = int(numerical_data[1].split()[0])
    ny = int(numerical_data[2].split()[0])
    nz = int(numerical_data[3].split()[0])
    dx = float(numerical_data[1].split()[1])
    dy = float(numerical_data[2].split()[2])
    dz = float(numerical_data[3].split()[3])
    
    # yes this is correct regardless of what
    cube['data'] = np.array(list(map(float, [ y for x in numerical_data[4+nat:] for y in x.split() ])))
    cube['header'] = numerical_data[:4+nat]
    #big_mat = np.zeros([nx, ny, nz])
    #big_mat = np.reshape(big_vect, [nz, ny, nx]) # note the order
    #print(big_mat.shape, big_mat[0][0][:10])
    
    # dimension?
    #z = 0
    #zi = int(z/dz)
    #print(zi)
    return cube

def print_charge(filename, cube):
    #print(cube['header'])
    #print(cube['data'])
    with open(filename, 'w') as fh:
        for line in cube['header']:
            fh.write(line)
        print(cube['data'].shape[0])
        cube['data'] = np.reshape(cube['data'], (int(cube['data'].shape[0]/6), 6))
        #fh.write(np.array2string(cube['data']))
        fh.write('\n'.join([ ' '.join([ str(y) for y in x ]) for x in cube['data']]))
    #    fh.write(cube['data'])

if __name__ == '__main__':
    density_files = argv[1:]
    assert len(density_files) == 2
    density0 = read_charge(density_files[0])
    density1 = read_charge(density_files[1])
    assert density0['header'] == density1['header']

    density_delta = defaultdict(list)
    density_delta['header'] = density0['header']
    density_delta['data'] = density0['data'] - density1['data']
    print_charge('delta.cube', density_delta)

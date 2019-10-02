#!/usr/bin/env python
# Note: does not use fancy processings;
# only valid for same-grid calculations

import numpy as np
import argparse
import copy
from collections import defaultdict

class QEScalarField(object):
    # this is not the best way to do things; but regardless a nice conversion
    # from the class-less initial form
    def __init__(self, comment=None, header=None, data=None, dr=(None,None,None)):
        self.comment = comment
        self.header = header
        self.data = data
        pass

    @classmethod
    def from_file(cls, filename):
        cube = defaultdict(list)
        with open(filename, 'r') as xx:
            # hand-handled
            lines = xx.readlines()
        comment = lines[:2]
        numerical_data = lines[2:]
        nat = int(numerical_data[0].split()[0])
        nx = int(numerical_data[1].split()[0])
        ny = int(numerical_data[2].split()[0])
        nz = int(numerical_data[3].split()[0])
        dx = float(numerical_data[1].split()[1])
        dy = float(numerical_data[2].split()[2])
        dz = float(numerical_data[3].split()[3])

        # yes this is correct regardless of what
        header = numerical_data[:4+nat]

        # first write in form of long vector, and just reshape according to the definitions in the file
        data = np.array(list(map(float, [ y for x in numerical_data[4+nat:] for y in x.split() ])))
        data = np.reshape(data, [nz, ny, nx]) # note the order

        # Real dimension?
        #z = 0
        #zi = int(z/dz)
        #print(zi)
        qescalarfield = cls(comment, header, data, (dx,dy,dz))
        return qescalarfield

    def to_file(self, filename):
        """ Assuming the charge in form of 3D-numpy array """
        data = np.reshape(self.data, (int(self.data.size/6), 6))
        with open(filename, 'w') as fh:
            for line in self.comment:
                fh.write(line)
            for line in self.header:
                fh.write(line)
            #print(cube['data'].shape[0])
            fh.write('\n'.join([ ' '.join([ str(y) for y in x ]) for x in data ]))

    def get_gradient(self):
        # TODO: scale according to the grid, + save
        self.gradient = np.gradient(self.data, self.dr)
        return self.gradient

    def get_reduced_gradient(self):
        """ Reduced density gradient (RDG); often used in context of non-covalent interactions """
        return np.abs(self.gradient) / ( self.gradient**(4./3.)*2*(3*np.pi**2)**(1/3.) )




# TODO: don't like this manual style; but not essential
# and not deterimental to the performance either
def read_charge(density_file):
    cube = defaultdict(list)
    with open(density_file, 'r') as xx:
        # hand-handled
        lines = xx.readlines()
    comment = lines[:2]
    numerical_data = lines[2:]
    nat = int(numerical_data[0].split()[0])
    nx = int(numerical_data[1].split()[0])
    ny = int(numerical_data[2].split()[0])
    nz = int(numerical_data[3].split()[0])
    dx = float(numerical_data[1].split()[1])
    dy = float(numerical_data[2].split()[2])
    dz = float(numerical_data[3].split()[3])

    # yes this is correct regardless of what
    cube['comment'] = comment
    cube['header'] = numerical_data[:4+nat]
    cube['data'] = np.array(list(map(float, [ y for x in numerical_data[4+nat:] for y in x.split() ])))
    cube['data'] = np.reshape(cube['data'], (int(cube['data'].shape[0]/6), 6))
    #big_mat = np.zeros([nx, ny, nz])
    #big_mat = np.reshape(big_vect, [nz, ny, nx]) # note the order
    #print(big_mat.shape, big_mat[0][0][:10])
    # dimension?
    #z = 0
    #zi = int(z/dz)
    #print(zi)
    return cube

def write_cube(filename, data):
    """ Assuming the charge in form of 3D-numpy array """
    with open(filename, 'w') as fh:
        for line in data['comment']:
            fh.write(comment)
        for line in data['header']:
            fh.write(line)
        #print(cube['data'].shape[0])
        fh.write('\n'.join([ ' '.join([ str(y) for y in x ]) for x in data['data']]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-filename', '-o', default='delta.cube')
    parser.add_argument('density_files', nargs=2)
    args = parser.parse_args()
    density_files = args.density_files
    #density0 = read_charge(density_files[0])
    #density1 = read_charge(density_files[1])
    density0 = QEScalarField.from_file(density_files[0])
    density1 = QEScalarField.from_file(density_files[1])
    #assert density0['header'] == density1['header']

    #density_delta = defaultdict(list)
    density_delta = copy.deepcopy(density0)
    #density_delta['comment'] = density0['comment']
    #density_delta['header'] = density0['header']
    #density_delta['data'] = density0['data'] - density1['data']
    density_delta.data = density0.data - density1.data
    #write_cube(args.output_filename, density_delta)
    density_delta.to_file(args.output_filename)

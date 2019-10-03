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
        self.dr = dr
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
        # TODO: using proper grid array in place of dr
        # currently will only work on cube cells

        # yes this is correct regardless of what
        header = numerical_data[:4+nat]

        # first write in form of long vector, and just reshape according to the definitions in the file
        data = np.array(list(map(float, [ y for x in numerical_data[4+nat:] for y in x.split() ])))
        #data = np.reshape(data, [nz, ny, nx]) # note the order
        data = np.reshape(data, [nx, ny, nz]) # note the order

        # Real dimension?
        #z = 0
        #zi = int(z/dz)
        #print(zi)
        qescalarfield = cls(comment, header, data, (dx,dy,dz))
        return qescalarfield

    def to_file(self, filename, datatype='charge'):
        """ Assuming the charge in form of 3D-numpy array """
        assert datatype == 'charge' or datatype == 'rdg' or datatype == 'gradient' or datatype == 'rdg-inv'
        with open(filename, 'w') as fh:
            for line in self.comment:
                fh.write(line)
            for line in self.header:
                fh.write(line)
            if datatype == 'charge':
                data = np.reshape(self.data, (int(self.data.size/6), 6))
                fh.write('\n'.join([ ' '.join([ str(y) for y in x ]) for x in data ]))
            elif datatype == 'rdg':
                data = np.reshape(self.rdg, (int(self.rdg.size/6), 6))
                fh.write('\n'.join([ ' '.join([ str(y) for y in x ]) for x in data ]))
            elif datatype == 'rdg-inv':
                data = np.reshape(self.rdg, (int(self.rdg.size/6), 6))
                data = 1./data
                fh.write('\n'.join([ ' '.join([ str(y) for y in x ]) for x in data ]))
            elif datatype == 'gradient':
                data = np.reshape(self.gradient, (int(self.gradient.size/6), 6))
                fh.write('\n'.join([ ' '.join([ str(y) for y in x ]) for x in data ]))

    def rdg_hist(self):
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots()
        flat_rdg = np.reshape(self.rdg.size, 1)
        flat_density = np.reshape(self.data.size, 1)
        #hist, bin_edges = np.histogram(np.hstack(flat_rdg, flat_density), density=True)
        ax.hist(np.hstack(flat_rdg, flat_density), density=True, bins='auto')
        plt.show()


    def get_gradient(self):
        # TODO: scale according to the grid, + save
        # misleading name; calculate the ABSOLUTE gradient; will change later
        gradients = np.gradient(self.data, *self.dr)
        print(self.data.size, gradients[0].size)
        self.gradient = np.sqrt(
                np.power(gradients[0],2) +
                np.power(gradients[1],2) +
                np.power(gradients[2],2))
        print(self.gradient.size)
        print(self.gradient.shape)
        return self.gradient

    def get_reduced_gradient(self):
        """ Reduced density gradient (RDG); often used in context of non-covalent interactions """
        self.rdg = self.gradient / ( np.power(self.data, 4./3.)*2*(3*np.pi**2)**(1./3.) )
        # test each term
        # self.rdg = self.gradient / np.power(self.data, 4./3.)
        print(self.rdg.size)
        print(self.rdg.shape)
        return self.rdg


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-filename', '-o', default='delta.cube')
    parser.add_argument('--type', '-t', type=str, default='delta',
            choices=['delta', 'gradient', 'rdg', 'rdg-inv', 'rdg-hist'])
    parser.add_argument('density_files', nargs='+')
    args = parser.parse_args()
    if args.type == 'delta':
        assert(len(args.density_files)) == 2
        density_files = args.density_files
        density0 = QEScalarField.from_file(density_files[0])
        density1 = QEScalarField.from_file(density_files[1])
        density_delta = copy.deepcopy(density0)
        density_delta.data = density0.data - density1.data
        density_delta.to_file(args.output_filename)
    elif args.type == 'rdg':
        assert(len(args.density_files)) == 1
        density = QEScalarField.from_file(args.density_files[0])
        density.get_gradient()
        density.get_reduced_gradient()
        density.to_file(args.output_filename, 'rdg')
    elif args.type == 'rdg-inv': # temporary; note that the critical point for rdgs are the zeros
        # just invert
        assert(len(args.density_files)) == 1
        density = QEScalarField.from_file(args.density_files[0])
        density.get_gradient()
        density.get_reduced_gradient()
        density.to_file(args.output_filename, 'rdg-inv')
    elif args.type == 'rdg-hist': # temporary; note that the critical point for rdgs are the zeros
        # just invert
        assert(len(args.density_files)) == 1
        density = QEScalarField.from_file(args.density_files[0])
        density.get_gradient()
        density.get_reduced_gradient()
        density.rdg_hist()
    elif args.type == 'gradient': # actually norm-gradient (scalar)
        assert(len(args.density_files)) == 1
        density = QEScalarField.from_file(args.density_files[0])
        density.get_gradient()
        density.to_file(args.output_filename, 'gradient')

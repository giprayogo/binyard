#!/usr/bin/env python
"""CUBE."""
import argparse
import numpy as np
from numpy.linalg import norm

class Cube():
    """Gaussian CUBE file.

    Format reference: http://paulbourke.net/dataformats/cube/"""
    def __init__(self, comments, nat, origin, grid, voxel, unit, species, charges, coordinates, volumetrics):
        self.comments = comments
        self.nat = nat
        self.origin = origin
        self.grid = grid
        self.voxel = voxel
        self.unit = unit
        self.species = species
        self.charges = charges
        self.coordinates = coordinates
        self.volumetrics = volumetrics

    @classmethod
    def from_file(cls, filename):
        """From file."""
        lines = None
        with open(filename, 'r') as f:
            lines = f.readlines()
        # Headers.
        comments = line[:2]
        natorigin = np.array(line[2])
        nat = natorigin[0]
        origin = natorigin[1:]
        voxelgrid = np.array(line[3:6])
        grid = np.abs(voxelgrid[:, 0])
        voxel = voxelgrid[:, 1:]
        unit = 'bohr' if (voxelgrid[:, 0] > 0).all() else 'angstrom'
        scc = np.fromstring(line[6:6+nat])
        species = scc[:, 0]
        charges = scc[:, 1]
        coordinates = scc[:, 2:]
        volumetrics = np.fromstring(line[6+nat:])
        return cls(comments, nat, origin, grid, voxel, unit, species, charges, coordinates, volumetrics)

    def __str__(self):
        string = ''
        for _ in comments:
            string += _
            string += '\n'
        string += str(nat)
        string += ' '.join(map(str, origin))
        string += '\n'
        string += self.np2d2str(np.hstack((self.grid, self.voxel)))
        string += self.np2d2str(np.hstack((self.species, self.charges, self.coordinates)))
        string += self.np2d2str(self.volumetrics)
        return string

    #@jit(nopython=True)
    @staticmethod
    def np2d2str(array):
        string = ''
        for np1d in array:
            string += ' '.join(map(str, np1d))
            string += '\n'
        return string

    def to_file(self, filename):
        with open(filename, 'w') as f:
            f.write(str(self))

    def tile(self, tilemat):
        """Resize the unit cell by the specified tiling matrix."""
        # Decide new voxel size. Keep voxel volume.
        pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('cubefile', help='Gaussian-style CUBE file')
    args = parser.parse_args()

    cubefile = args.cubefile
    cube = Cube.from_file(cubefile)
    print(cube)

if __name__ == '__main__':
    main()


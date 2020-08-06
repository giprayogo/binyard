#!/usr/bin/env python
"""Tiling of CUBE with trilinear interpolation."""
import argparse
import time
from itertools import product
import sys
import numpy as np
from numpy.linalg import norm, inv
from numba import jit

class Cube():
    """Gaussian CUBE file.

    Format reference: http://paulbourke.net/dataformats/cube/"""
    def __init__(self, comments, nat, origin, grid, voxel, unit, species, charges,
                 coordinates, volumetrics):
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

        # Derived stuffs.
        self.cell = (self.voxel.T * self.grid).T
        self.icell = inv(self.cell)

    @classmethod
    def from_file(cls, filename):
        """From file."""
        lines = None
        with open(filename, 'r') as f:
            lines = f.readlines()
        # Headers.
        comments = [x.strip() for x in lines[:2]]
        natorigin = np.fromstring(lines[2], sep=' ')
        nat = natorigin[0].astype(np.int64)
        origin = natorigin[1:]
        voxelgrid = Cube.strit2np2d(lines[3:6])
        grid = np.abs(voxelgrid[:, 0]).astype(np.int64)
        voxel = voxelgrid[:, 1:]
        unit = 'bohr' if (voxelgrid[:, 0] > 0).all() else 'angstrom'
        scc = Cube.strit2np2d(lines[6:6+nat])
        species = scc[:, 0].astype(np.int64)
        charges = scc[:, 1].astype(np.int64)
        coordinates = scc[:, 2:]
        volumetrics = Cube.strit2np2d(lines[6+nat:])
        volumetrics = np.reshape(volumetrics, grid)
        return cls(comments, nat, origin, grid, voxel, unit, species, charges,
                   coordinates, volumetrics)

    def __str__(self):
        string = ''
        for _ in self.comments:
            string += _
            string += '\n'
        string += str(self.nat)
        string += ' '
        string += ' '.join(map(str, self.origin))
        string += '\n'
        string += self.np2d2str(np.hstack((np.reshape(self.grid, (3, 1)), self.voxel)),
                                fmt='{:.0f} {:.15f} {:.15f} {:.15f}')
        string += self.np2d2str(np.hstack((np.reshape(self.species, (self.species.shape[0], 1)),
                                           np.reshape(self.charges, (self.charges.shape[0], 1)),
                                           self.coordinates)),
                                fmt='{:.0f} {:.0f} {:.15f} {:.15f} {:.15f}')
        string += self.np2d2str(np.reshape(self.volumetrics, (-1, 6)))
        return string

    def to_file(self, filename):
        """Well what else."""
        with open(filename, 'w') as f:
            f.write(str(self))

    @staticmethod
    def np2d2str(array, fmt=None):
        """Numpy 2d to string."""
        string = ''
        if fmt is None:
            for np1d in array:
                string += ' '.join(map(str, np1d))
                string += '\n'
            return string
        for np1d in array:
            string += fmt.format(*np1d)
            string += '\n'
        return string

    @staticmethod
    def strit2np2d(iterable):
        """String iterable to 2d Numpy array."""
        array = []
        for _ in iterable:
            array.append(np.fromstring(_, sep=' '))
        return np.array(array)

    @staticmethod
    def lte(a, b, rtol=1e-05, atol=1e-08, equal_nan=False):
        """Less than equal for floats."""
        return (a <= b).all() or np.allclose(a, b, rtol=rtol, atol=atol, equal_nan=equal_nan)

    @staticmethod
    def lt(a, b, rtol=1e-05, atol=1e-08, equal_nan=False):
        """Less than for floats."""
        return (a <= b).all() and not np.allclose(a, b, rtol=rtol, atol=atol, equal_nan=equal_nan)

    @staticmethod
    def gte(a, b, rtol=1e-05, atol=1e-08, equal_nan=False):
        """Greater than equal for floats."""
        return (a >= b).all() or np.allclose(a, b, rtol=rtol, atol=atol, equal_nan=equal_nan)

    @staticmethod
    def vol(cell):
        """Volume enclosed by 3-vector."""
        return np.abs(np.dot(np.cross(cell[0], cell[1]), cell[2]))


    @staticmethod
    @jit(nopython=True)
    def tl_interpolate(p, grid, volumetric):
        """Trilinear interpolation of point values to the original point."""
        # Map point to primitive cell, in "grid" basis
        # lower and upper

        p0 = np.floor(p)
        p1 = p0+1.
        # Only for taking volumetric's values
        pm0 = np.mod(p0, grid).astype(np.int64)
        pm1 = np.mod(p1, grid).astype(np.int64)
        mat = np.array([
            [1, p0[0], p0[1], p0[2], p0[0]*p0[1], p0[0]*p0[2], p0[1]*p0[2], p0[0]*p0[1]*p0[2]],
            [1, p1[0], p0[1], p0[2], p1[0]*p0[1], p1[0]*p0[2], p0[1]*p0[2], p1[0]*p0[1]*p0[2]],
            [1, p0[0], p1[1], p0[2], p0[0]*p1[1], p0[0]*p0[2], p1[1]*p0[2], p0[0]*p1[1]*p0[2]],
            [1, p1[0], p1[1], p0[2], p1[0]*p1[1], p1[0]*p0[2], p1[1]*p0[2], p1[0]*p1[1]*p0[2]],
            [1, p0[0], p0[1], p1[2], p0[0]*p0[1], p0[0]*p1[2], p0[1]*p1[2], p0[0]*p0[1]*p1[2]],
            [1, p1[0], p0[1], p1[2], p1[0]*p0[1], p1[0]*p1[2], p0[1]*p1[2], p1[0]*p0[1]*p1[2]],
            [1, p0[0], p1[1], p1[2], p0[0]*p1[1], p0[0]*p1[2], p1[1]*p1[2], p0[0]*p1[1]*p1[2]],
            [1, p1[0], p1[1], p1[2], p1[0]*p1[1], p1[0]*p1[2], p1[1]*p1[2], p1[0]*p1[1]*p1[2]]])
        c = np.array([
            volumetric[pm0[0], pm0[1], pm0[2]],
            volumetric[pm1[0], pm0[1], pm0[2]],
            volumetric[pm0[0], pm1[1], pm0[2]],
            volumetric[pm1[0], pm1[1], pm0[2]],
            volumetric[pm0[0], pm0[1], pm1[2]],
            volumetric[pm1[0], pm0[1], pm1[2]],
            volumetric[pm0[0], pm1[1], pm1[2]],
            volumetric[pm1[0], pm1[1], pm1[2]]])
        a = inv(mat) @ c
        return a[0] + a[1]*p[0] + a[2]*p[1] + a[3]*p[2] + \
            a[4]*p[0]*p[1] + a[5]*p[0]*p[2] + a[6]*p[1]*p[2] + \
            a[7]*p[0]*p[1]*p[2]

    @staticmethod
    def nn_interpolate(p, grid, volumetric):
        """Nearest neighbor interpolation of point values to the original point."""
        # Map point to primitive cell, in "grid" basis
        pp = np.mod(np.round(p).astype(int), grid)
        return volumetric[tuple(pp)]

    @staticmethod
    def fill(fn, grid, ngrid, voxel, volumetric, icell, j=2):
        """Fill grid with fn values. Multithreaded"""
        def p_grid(index, grid, icell):
            """Get point in grid unit from the specified voxel index and cell."""
            return ((voxel.T * index).T.sum(axis=0) @ icell) * grid

        a = np.empty(ngrid)
        for k in product(range(ngrid[0]), range(ngrid[1]), range(ngrid[2])):
            a[k] = fn(p_grid(k, grid, icell), grid, volumetric)
        return a

    def tile(self, tilemat):
        """Resize the unit cell by the specified tiling matrix. In-place."""
        det = np.linalg.det(tilemat)
        scale = np.abs(np.linalg.det(tilemat))
        # Scale unit cell.
        self.nat *= scale
        cellp = tilemat @ self.cell
        #print(self.cell)
        #print(cellp)
        fracsp = self.coordinates @ inv(cellp) # Fractional coordinate in the new cell.

        it = inv(tilemat) # cell in cellp des.

        # Atomic coordinate tiling. Inefficient quick way.
        nmi = tilemat.min().astype(int)
        nm = tilemat.max().astype(int)
        _coords = []
        _species = []
        _charges = []
        # Find new cell's extremum.
        corners = np.array([(ijk * cellp.T).T.sum(axis=0) @ self.icell
                            for ijk in product((0,1), repeat=3)])
        # Rounded (magnitude-wise) up.
        def mround(e):
            return (np.sign(e) * np.ceil(np.round(np.abs(e), 10))).astype(int)
        corners = mround(corners)
        # expanded just in case.
        rx = (min(corners[:, 0])-1, max(corners[:, 0])+1)
        ry = (min(corners[:, 1])-1, max(corners[:, 1])+1)
        rz = (min(corners[:, 2])-1, max(corners[:, 2])+1)

        for r, s, c in zip(fracsp, self.species, self.charges):
            for ijk in product(range(*rx), range(*ry), range(*rz)):
                thing = r + (ijk * it.T).T.sum(axis=0)
                if self.lt(thing, 1.0) and self.gte(thing, 0.):
                    _coords.append(thing @ cellp)
                    _species.append(s)
                    _charges.append(c)
        if len(_coords) != self.nat:
            raise RuntimeError(f"Wrong tiling of coordinates ({len(_coords)}/{self.nat}).")
        self.coordinates = np.array(_coords)
        self.species = np.array(_species)
        self.charges = np.array(_charges)


        # Charge density tiling.
        # Scale to keep voxel volume the same first,
        # then choose nearest integer grid size.
        scalenb = (self.vol(self.cell) / self.vol(cellp)) ** (1/3)
        nvoxel = scalenb * (self.voxel @ self.icell) @ cellp
        # The voxel are parallel to the cell so we can do this.
        ngrid = (norm(cellp, axis=1) / norm(nvoxel, axis=1)).round().astype(int)
        # Try to make the grid divisible by 6, whilst making minimal changes to the shape.
        # Largest integer has lower fractional changes.
        if (ngrid.prod() % 6):
            order = np.argsort(ngrid)
            largest_i = np.where(order == 2)[0]
            sec_largest_i = np.where(order == 1)[0]
            if (ngrid.prod() % 3) and (ngrid.prod() % 2):
                ngrid[largest_i] += 3 - (ngrid[largest_i] % 3)
                ngrid[sec_largest_i] += ngrid[sec_largest_i] % 2
            elif (ngrid.prod() % 3):
                ngrid[largest_i] += 3 - (ngrid[largest_i] % 3)
            else:
                ngrid[largest_i] += ngrid[largest_i] % 2
        # Resize the voxel for an integer grid
        nvoxel = (cellp.T / ngrid).T
        start = time.time()
        nvolumetric = self.fill(self.tl_interpolate, self.grid, ngrid,
                                nvoxel, self.volumetrics, self.icell)
        end = time.time()
        print(f"Filled in {end-start} secs.", file=sys.stderr)
        self.volumetrics = nvolumetric
        self.grid = ngrid
        self.voxel = nvoxel

def main():
    """Main."""
    parser = argparse.ArgumentParser()
    parser.add_argument('cubefile', help="Gaussian-style CUBE file")
    parser.add_argument('tilemat', help="Tiling matrix")
    args = parser.parse_args()
    tilemat = np.fromstring(args.tilemat, sep=' ')
    tilemat = tilemat.reshape(3, 3)

    cubefile = args.cubefile
    cube = Cube.from_file(cubefile)
    cube.tile(tilemat)
    print(cube)

if __name__ == '__main__':
    main()

#!/usr/bin/env python
"""Tiling of CUBE with trilinear interpolation."""
import argparse
import time
from itertools import product
import sys
from lxml import etree
import h5py
import numpy as np
from numpy.linalg import norm, inv
from numba import jit

atomid = {
        'Li': '3',
        'V': '23',
        'O': '8',
        'S': '16',
        'Se': '34',
        'C': '6',
        'Si': '14',
        'H': '1',
        'N': '7',
        }

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
        volumetrics = Cube.strit2np1d(lines[6+nat:])
        volumetrics = np.reshape(volumetrics, grid)
        return cls(comments, nat, origin, grid, voxel, unit, species, charges,
                   coordinates, volumetrics)

    def get_header_from_xml(xmlfile):
        """ Parse grid information from QMCPACK's XML.
        Quick-patched from h5tocube.py"""
        meta = dict()
        tree = etree.parse(xmlfile)

        # Kind of estimator.
        if tree.xpath("//estimator[@type='spindensity']"):
            meta['estimator'] = 'spindensity'
        elif tree.xpath("//estimator[@type='density']"):
            meta['estimator'] = 'density'
        else:
            meta['estimator'] = None
        # Only support density for now.
        assert meta['estimator'] == 'density'

        for lattice in tree.xpath("///parameter[@name='lattice']"):
            lattice = np.array(list(map(float, lattice.text.split())))
            lattice = lattice.reshape(-1, 3)
        for _ in tree.xpath("//estimator[@type='density']"):
            delta = np.array([ float(x) for x in _.get('delta').split() ])
            meta['grid'] = [int(x) for x in 1/delta ]
            meta['dr'] = [x[0]/x[1] for x in zip(lattice, meta['grid'])]

        for positions in tree.xpath("//attrib[@name='position']"):
            position = np.array(list(map(float, positions.text.split())))
            position = position.reshape(-1, 3)
            # remember that the positions are in fractional coordinates
            #meta['position'] = [sum([ y[0]*y[1] for y in zip(x, lattice) ]) for x in position]
            meta['coordinates'] = position
        for ionid in tree.xpath("//attrib[@name='ionid']"):
            i = [ atomid[x.strip('0123456789')] for x in ionid.text.split()]
            meta['species'] = np.array([x for x in i])
            meta['charges'] = np.array([x for x in i]) # We never do weird things here.

        meta['comments'] = ('QMCPACK density/spin density data\n'
                            f'source file: {xmlfile}\n')

        meta['nat'] = meta['species'].size
        meta['origin'] = np.array([0., 0., 0.]) # Assume always so.
        meta['unit'] = 'bohr'
        meta['voxel'] = np.vstack(meta['dr'])

        return meta

    @classmethod
    def from_qmcpack_files(cls, h5_filename, xml_filename, e):
     """From QMCPACK's h5 file. Density estimator only, no twist averaging.
     Patched in from h5tocube.py"""

     xml_meta = cls.get_header_from_xml(xml_filename)
     comments = xml_meta['comments']
     nat = xml_meta['nat']
     origin = xml_meta['origin']
     grid = xml_meta['grid']
     voxel = xml_meta['voxel']
     unit = xml_meta['unit']
     species = xml_meta['species']
     charges = xml_meta['charges']
     coordinates = xml_meta['coordinates']

     f = h5py.File(h5_filename, 'r')
     u = f['Density']['value'][e:]
     # TODO: no +-bar for now
     volumetrics = np.array(u).mean(axis=0)[e:]
     return cls(comments, nat, origin, grid, voxel, unit, species, charges,
               coordinates, volumetrics)

    @classmethod
    def from_block_header(cls, header, volumetrics):
        """From defined "header" and "volumetrics" section."""
        # Headers.
        lines = header.split('\n')

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
        # TODO: This part
        # string += self.np2d2str(np.reshape(self.volumetrics, (-1, 6)))
        print("Writing", file=sys.stderr)
        # Proper format
        x, y, z = self.volumetrics.shape
        # Quick fix
        was_newline = False
        for i in range(x):
            for j in range(y):
                for k in range(z):
                    was_newline = False
                    string += f"{self.volumetrics[i][j][k]} "
                    if (k % 6) == 5:
                        string += "\n"
                        was_newline = True
                if not was_newline:
                    string += "\n"
        return string.strip()

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
    def strit2np1d(iterable):
        """String iterable to 1d Numpy array."""
        array = []
        for _ in iterable:
            array.append(np.fromstring(_, sep=' '))
        return np.concatenate(array)

    @staticmethod
    def strit2np2d(iterable):
        """String iterable to 2d Numpy array."""
        array = []
        for _ in iterable:
            array.append(np.fromstring(_, sep=' '))
        # return np.array(array)
        # return np.concatenate(array)
        return np.stack(array)

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

    def tile(self, tilemat, target_grid=None):
        """Resize the unit cell by the specified tiling matrix. In-place."""
        det = np.linalg.det(tilemat)
        scale = np.abs(np.linalg.det(tilemat))
        # Scale unit cell.
        self.nat *= scale
        cellp = tilemat @ self.cell
        #print(self.cell)
        #print(cellp)
        icellp = inv(cellp)
        fracsp = self.coordinates @ icellp # Fractional coordinate in the new cell.

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

        def isthere(objlist, obj, ops):
            #print(obj)
            for friend in objlist:
                ffriend = friend @ icellp
                #print('-------------------------')
                #print(ffriend)
                for op in ops:
                    #print(op)
                    friendrep = ffriend + op
                    #print(f"    {friendrep}")
                    if np.isclose(friendrep, obj, atol=1.0e-4).all():
                        return True
            return False

        for r, s, c in zip(fracsp, self.species, self.charges):
            for ijk in product(range(*rx), range(*ry), range(*rz)):
                thing = r + (ijk * it.T).T.sum(axis=0)
                if self.lte(thing, 1.0) and self.gte(thing, 0.):
                    # See if equivalent exists in the coordinate list.
                    if isthere(_coords, thing, list(product((-1, 0, 1), repeat=3))):
                        continue
                    _coords.append(thing @ cellp)
                    _species.append(s)
                    _charges.append(c)
        if len(_coords) != int(self.nat):
            print(np.round(_coords @ icellp, 4))
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
        if target_grid is None:
            ngrid = (norm(cellp, axis=1) / norm(nvoxel, axis=1)).round().astype(int)
        else:
            ngrid = target_grid

        self.regrid(ngrid)
        # Try to make the grid divisible by 6, whilst making minimal changes to the shape.
        # Largest integer has lower fractional change.
        # if (ngrid.prod() % 6):
        #     order = np.argsort(ngrid)
        #     largest_i = np.where(order == 2)[0]
        #     sec_largest_i = np.where(order == 1)[0]
        #     if (ngrid.prod() % 3) and (ngrid.prod() % 2):
        #         ngrid[largest_i] += 3 - (ngrid[largest_i] % 3)
        #         ngrid[sec_largest_i] += ngrid[sec_largest_i] % 2
        #     elif (ngrid.prod() % 3):
        #         ngrid[largest_i] += 3 - (ngrid[largest_i] % 3)
        #     else:
        #         ngrid[largest_i] += ngrid[largest_i] % 2
        # # Resize the voxel for an integer grid
        # nvoxel = (cellp.T / ngrid).T
        # start = time.time()
        # nvolumetric = self.fill(self.tl_interpolate, self.grid, ngrid,
        #                         nvoxel, self.volumetrics, self.icell)
        # end = time.time()
        # print(f"Filled in {end-start} secs.", file=sys.stderr)
        # self.volumetrics = nvolumetric
        # self.grid = ngrid
        # self.voxel = nvoxel

    def regrid(self, ngrid):
        """Adjust grid size. In-place."""
        # Try to make the grid divisible by 6, whilst making minimal changes to the shape.
        # Largest integer has lower fractional change.
        # NOTE: not necessary!
        # if (ngrid.prod() % 6):
        #     order = np.argsort(ngrid)
        #     largest_i = np.where(order == 2)[0]
        #     sec_largest_i = np.where(order == 1)[0]
        #     if (ngrid.prod() % 3) and (ngrid.prod() % 2):
        #         ngrid[largest_i] += 3 - (ngrid[largest_i] % 3)
        #         ngrid[sec_largest_i] += ngrid[sec_largest_i] % 2
        #     elif (ngrid.prod() % 3):
        #         ngrid[largest_i] += 3 - (ngrid[largest_i] % 3)
        #     else:
        #         ngrid[largest_i] += ngrid[largest_i] % 2
        # Resize the voxel for an integer grid
        print(f"Re-grid from {self.grid} to {ngrid}", file=sys.stderr)
        nvoxel = (self.cell.T / ngrid).T
        start = time.time()
        nvolumetric = self.fill(self.tl_interpolate, self.grid, ngrid,
                                nvoxel, self.volumetrics, self.icell)
        end = time.time()
        print(f"Filled in {end-start} secs.", file=sys.stderr)
        self.volumetrics = nvolumetric
        self.grid = ngrid
        self.voxel = nvoxel

    def normalize(self):
        """Normalize volumetric data"""
        volumetric_sum = np.sum(self.volumetrics)
        self.volumetrics /= volumetric_sum

    def __sub__(self, other):
        volchange = self.volumetrics - other.volumetrics
        return Cube(
            self.comments,
            self.nat,
            self.origin,
            self.grid,
            self.voxel,
            self.unit,
            self.species,
            self.charges,
            self.coordinates,
            volchange
        )

def main():
    """Main."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--cubefile', help="Gaussian-style CUBE file")
    parser.add_argument('--sub-cubefile', help="Gaussian-style CUBE file for substraction", default=None)
    parser.add_argument('--tilemat', help="Tiling matrix", default=None)
    parser.add_argument('--normal', help="Normalize volumetric data", action="store_true")
    parser.add_argument('--cube-grid', help="Volumetric grid", default=None)
    parser.add_argument('--qmcpack', action='store_true', help="QMCPACK mode")
    parser.add_argument('--h5-file', '-d', help="QMCPACK HDF5")
    parser.add_argument('--xml-file', '-x', help="QMCPACK XML")
    parser.add_argument('-e', help="QMCPACK equilibration", default=0)
    args = parser.parse_args()
    qmcpack_mode = args.qmcpack
    h5file = args.h5_file
    xmlfile = args.xml_file
    e = args.e

    cubefile = args.cubefile

    if args.sub_cubefile is not None:
        cube = Cube.from_file(cubefile)
        sub_cubefile = Cube.from_file(args.sub_cubefile)
        cube = cube - sub_cubefile
    else:
        if qmcpack_mode:
            cube = Cube.from_qmcpack_files(h5file, xmlfile, e)
        else:
            cube = Cube.from_file(cubefile)

        if args.tilemat is not None:
            tilemat = np.fromstring(args.tilemat, sep=' ', dtype=int)
            tilemat = tilemat.reshape(3, 3)

            if args.cube_grid is None:
                cube.tile(tilemat)
            else:
                grid = np.fromstring(args.cube_grid, sep=' ', dtype=int)
                cube.tile(tilemat, grid)
        else:
            if args.cube_grid is not None:
                grid = np.fromstring(args.cube_grid, sep=' ', dtype=int)
                cube.regrid(grid)

        if args.normal:
            cube.normalize()

    print(cube)

if __name__ == '__main__':
    main()

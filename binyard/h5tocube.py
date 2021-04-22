#!/usr/bin/env python
"""Convert QMCPACK *.stat.h5 densities/spin-densities to Gaussian CUBE."""
import argparse
import re
import h5py
import numpy as np
from lxml import etree
from numpy.linalg import norm
from cubetiler import Cube

SERIES_REGEX = re.compile(r'(?<=s)[0-9]+')
TWIST_REGEX = re.compile(r'(?<=tw)[0-9]+')

def single_search(regex, string, default=None):
    """First-match search of a string given a regex. Catch non-match into default."""
    match = regex.search(string)
    if not match:
        return default
    return match.group(0)

atomid = {
        'Li': '3',
        'V': '23',
        'O': '8',
        'S': '16',
        'Se': '34',
        'C': '6',
        'Si': '14',
        'H': '1'
        }

def esttype(xmlfile):
    """ Get estimator type from QMCPACK input file """
    tree = etree.parse(xmlfile)
    for _ in tree.xpath("//estimator[@type='spindensity']"):
        return 'spindensity'
    for _ in tree.xpath("//estimator[@type='density']"):
        return 'density'
    raise TypeError # no estimator


# Note: if I want to generalize: just make a superclass of this
# over-functionalizing functions seems to make it more difficult
class ScalarField(object):
    def __init__(self, xmlfile, scalarfiles, e):
        """ Parse grid information from QMCPACK's XML """
        # no need to keep the tree within the object
        tree = etree.parse(xmlfile)
        # also hack for others
        self.estimator = esttype(xmlfile)
        estimator = self.estimator

        # temporary hack for h00
        self.xmlfile = xmlfile

        self.e = e
        e = self.e

        # whatever this lattice is
        for lattice in tree.xpath("///parameter[@name='lattice']"):
            l = np.array(list(map(float, lattice.text.split())))
            l = l.reshape(-1, 3)
        nl = [ norm(x) for x in l ]

        # how to generalize instead of doing specifics for split h5-XML?

        # different tree tracing with it
        # grid determination; for now no need to care about the
        # exact form of grid and dr
        if self.estimator == 'spindensity':
            for _ in tree.xpath("///parameter[@name='dr']"):
                dr = [ float(x) for x in _.text.split() ]
                # because it is rounded up for integer grid
                self.grid = [ int(np.ceil(x[0]/x[1])) for x in zip(nl,dr) ]
                self.dr = [ x[0]/x[1] for x in zip(l, self.grid) ]
            try:
                self.grid
            except NameError:
                for _ in tree.xpath("///parameter[@name='grid']"):
                    self.grid = _.text.split()
                    self.dr = [ x[0]/x[1] for x in zip(l, self.grid) ]
        elif self.estimator == 'density':
            for _ in tree.xpath("//estimator[@type='density']"):
                delta = np.array([ float(x) for x in _.get('delta').split() ])
                self.grid = [ int(x) for x in 1/delta ]
                self.dr = [ x[0]/x[1] for x in zip(l, self.grid) ]

        for positions in tree.xpath("//attrib[@name='position']"):
            p = np.array(list(map(float, positions.text.split())))
            p = p.reshape(-1, 3)
            # remember that the positions are in fractional coordinates
            self.p = [ sum([ y[0]*y[1] for y in zip(x,l) ]) for x in p ]
        for ionid in tree.xpath("//attrib[@name='ionid']"):
            i = [ atomid[x.strip('0123456789')] for x in ionid.text.split() ]
            self.i = [ [x,x] for x in i ]

        # end of XML parser
        # start of h5 parser
        # TODO: also no reblocking here

        self.scalar = {}
        scalar = self.scalar
        if estimator == 'spindensity':
            for h5file in scalarfiles:
                f = h5py.File(h5file, 'r')
                # NOTE: passive rename, functionalize for more general
                #series = h5file.split('.')[2]
                #twist = h5file.split('.')[0].split('-')[-1]
                series = single_search(SERIES_REGEX, h5file, '000')
                twist = single_search(TWIST_REGEX, h5file, 0)

                # up and down densities, complete
                # NOTE: the format here change depending on QMCPACK version
                # functionalize for more general
                u = f['Density']['u']['value'][e:]
                d = f['Density']['d']['value'][e:]

                # Initialize the dict in dict
                scalar.setdefault(series, {})
                scalar[series].setdefault('u', {})
                #scalar[series].setdefault('ub', {})
                scalar[series].setdefault('d', {})
                #scalar[series].setdefault('db', {})

                # TODO: wrong child-ing?
                scalar[series]['u'][twist] = np.array(u)
                scalar[series]['d'][twist] = np.array(d)

        elif estimator == 'density':
            for h5file in scalarfiles:
                # see the repeated pattern?
                f = h5py.File(h5file, 'r')
                #series = h5file.split('.')[2]
                #twist = h5file.split('.')[0].split('-')[-1]
                series = single_search(SERIES_REGEX, h5file, '000')
                twist = single_search(TWIST_REGEX, h5file, 0)

                # this can be generalized with the previous one
                u = f['Density']['value'][e:]

                scalar.setdefault(series, {})
                scalar[series].setdefault('u', {})

                # as well as this one
                scalar[series]['u'][twist] = np.array(u)
                # note: just read; don't call statistical processings when not calling
    # up to here is OK


    # to generate function which returns correct one
    def h5extractgenerator(self):
        estimator = self.estimator
        if estimator == 'density':
            pass

    #NOTE: I can't seem to decide a nice interface for this one
    # Yes we don't need, generalization is in superclass
    #def statistic(self, twist=None):
    #    """ If twist is not specified, also do twist averages """
    #    scalar = self.scalar

    #    if estimator == 'density':
    #        if twist:
    #            # single twist
    #            u = scalar[series]['u'][twist].mean(0)
    #            ub = scalar[series]['u'][twist].std(0)
    #            return (u, ub)
    #        else:
    #            # twist averages
    #            us = [ x.mean(0) for x in scalar[series]['u'].values() ]
    #            ubs = [ x.std(0) for x in scalar[series]['u'].values() ]
    #            u = np.array(us).mean(0)
    #            ub = np.array(ubs).std(0)
    #            return (u, ub)
    #    elif estimator == 'spindensity':
    #        pass

    #            #density[series].setdefault('ub', {})
    #            #density[series]['u'][twist] = u.mean(0)
    #            #density[series]['ub'][twist] = u.std(0)

    #            # set this separately
    #            density[series].setdefault('u', {})
    #            density[series].setdefault('ub', {})
    #            density[series].setdefault('d', {})
    #            density[series].setdefault('db', {})
    #            density[series]['u'][twist] = u.mean(0)
    #            density[series]['ub'][twist] = u.std(0)
    #            density[series]['d'][twist] = d.mean(0)
    #            density[series]['db'][twist] = d.std(0)

    #        for serie in density.keys():
    #            um = np.array(list(density[serie]['u'].values()))
    #            ub = np.array(list(density[serie]['ub'].values()))
    #            dm = np.array(list(density[serie]['d'].values()))
    #            db = np.array(list(density[serie]['db'].values()))

    #            # the twist averaging
    #            # oh ok actually correct!
    #            um = um.mean(0)
    #            dm = dm.mean(0)
    #            ub = np.sqrt(sum([ x**2 for x in ub ]))
    #            db = np.sqrt(sum([ x**2 for x in db ]))
    #            udb = np.sqrt(sum([ x**2 for x in [ub,db] ]))

    # TODO: let's make it allows skipping twist averaging if wanted
    def to_file(self):
        """ Statistical process + save as *.cube file """
        scalar = self.scalar
        estimator = self.estimator
        header = self.get_cube_header()

        # i.e. never mix series!
        # TODO: is there a better name than "val"?
        #print(scalar.keys())
        for serie, val in scalar.items():
            # first do the statistical processing
            # get the objects
            u = val['u']
            #print(u)
            #exit()
            # also look to minimize repetitive patterns between u and d
            # I don't want to use this one too
            #print(list(u.values())[0])
            #print(list(u.values())[0].shape)

            umeans = [ x.mean(axis=0) for x in u.values() ]
            ustds = [ x.std(axis=0) for x in u.values() ]
            #print(len(umeans))
            #print(umeans[0].shape)
            #exit()

            assert len(umeans) == len(ustds)
            # twist averaging it is
            if len(umeans) > 1:
                um = umeans.mean(axis=0)
                ub = np.sqrt(sum([ x**2 for x in ustds ]))
            else:
                um = umeans[0]
                ub = ustds[0]

            if estimator == 'density':
                # Scale for 6-divisibility (CUBE file limitation)
                cube_u = Cube.from_block_header(header, um)
                cube_up = Cube.from_block_header(header, um-ub)
                cube_um = Cube.from_block_header(header, um+ub)
                # Standardized size
                cube_u.regrid(np.array([100, 100, 100]))
                cube_up.regrid(np.array([100, 100, 100]))
                cube_um.regrid(np.array([100, 100, 100]))

                cube_u.to_file(self.xmlfile.replace('.xml', '.Density_u.cube'))
                cube_up.to_file(self.xmlfile.replace('.xml', '.Density_u-err.cube'))
                cube_um.to_file(self.xmlfile.replace('.xml', '.Density_u+err.cube'))

                #np.savetxt('qmc.'+serie+'.Density_u.cube', um, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.Density_u-err.cube', um-ub, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.Density_u+err.cube', um+ub, header=header, comments='')
            elif estimator == 'spindensity':
                # Old implementation
                # this part for writing only
                # for the weird *.cube 6-shape (same padlength for everything)
                padlength = um.shape[0] % 6
                um = np.append(um, np.zeros(padlength))
                ub = np.append(ub, np.zeros(padlength))
                um = um.reshape(-1, 6)
                ub = ub.reshape(-1, 6)
                d = val['d']

                dmeans = [ x.mean() for x in d ]
                dstds = [ x.std() for x in d ]

                dm = dmeans.mean(0)
                db = np.sqrt(sum([ x**2 for x in dstds ]))

                # for the cross values
                # TODO: is this correct?
                udb = np.sqrt(sum([ x**2 for x in [ustds,dstds] ]))

                dm = np.append(dm, np.zeros(padlength))
                db = np.append(db, np.zeros(padlength))
                udb = np.append(udb, np.zeros(padlength))

                dm = dm.reshape(-1, 6)
                db = db.reshape(-1, 6)
                udb = udb.reshape(-1, 6)

                np.savetxt('qmc.'+serie+'.SpinDensity_d.cube', dm, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_d-err.cube', dm-db, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_d+err.cube', dm+db, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_u+d.cube', um+dm, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_u+d-err.cube', um+dm-udb, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_u+d+err.cube', um+dm+udb, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_u-d.cube', um-dm, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_u-d-err.cube', um-dm-udb, header=header, comments='')
                np.savetxt('qmc.'+serie+'.SpinDensity_u-d+err.cube', um-dm+udb, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u.cube', um, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u-err.cube', um-ub, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u+err.cube', um+ub, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_d.cube', dm, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_d-err.cube', dm-db, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_d+err.cube', dm+db, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u+d.cube', um+dm, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u+d-err.cube', um+dm-udb, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u+d+err.cube', um+dm+udb, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u-d.cube', um-dm, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u-d-err.cube', um-dm-udb, header=header, comments='')
            #np.savetxt('qmc.'+serie+'.SpinDensity_u-d+err.cube', um-dm+udb, header=header, comments='')


                # this is becaus I pre-averaged in the previous implementation
                # now I have to calculate all averages
                #um = np.array(list(scalar[serie]['u'].values()))
                #ub = np.array(list(scalar[serie]['ub'].values()))
                #dm = np.array(list(scalar[serie]['d'].values()))
                #db = np.array(list(scalar[serie]['db'].values()))

                ## statistical processing
                ## twist averaging it is
                #um = um.mean(0)
                #ub = np.sqrt(sum([ x**2 for x in ub ]))

                #dm = dm.mean(0)
                #db = np.sqrt(sum([ x**2 for x in db ]))

                #udb = np.sqrt(sum([ x**2 for x in [ub,db] ]))

                ## this part for writing only
                ## for the weird *.cube 6-shape (same padlength for everything)
                #padlength = um.shape[0] % 6

                #um = np.append(um, np.zeros(padlength))
                #ub = np.append(ub, np.zeros(padlength))

                #dm = np.append(dm, np.zeros(padlength))
                #db = np.append(db, np.zeros(padlength))

                #udb = np.append(udb, np.zeros(padlength))

                ## reshape
                #um = um.reshape(-1, 6)
                #ub = ub.reshape(-1, 6)

                #dm = dm.reshape(-1, 6)
                #db = db.reshape(-1, 6)

                #udb = udb.reshape(-1, 6)
                #np.savetxt('qmc.'+serie+'.SpinDensity_u.cube', um, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u-err.cube', um-ub, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u+err.cube', um+ub, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_d.cube', dm, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_d-err.cube', dm-db, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_d+err.cube', dm+db, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u+d.cube', um+dm, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u+d-err.cube', um+dm-udb, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u+d+err.cube', um+dm+udb, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u-d.cube', um-dm, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u-d-err.cube', um-dm-udb, header=header, comments='')
                #np.savetxt('qmc.'+serie+'.SpinDensity_u-d+err.cube', um-dm+udb, header=header, comments='')
        #elif estimator == 'density':
        #    for h5file in args.f:
        #        f = h5py.File(h5file, 'r')
        #        u = f['Density']['value'][e:]
        #        series = h5file.split('.')[2]
        #        twist = h5file.split('.')[0].split('-')[-1]
        #        density.setdefault(series, {})
        #        density[series].setdefault('u', {})
        #        density[series].setdefault('ub', {})
        #        density[series]['u'][twist] = u.mean(0)
        #        density[series]['ub'][twist] = u.std(0)


        #    for serie in density.keys():
        #        # for all twists
        #        # technically this way it is statistically wrong,
        #        # fix it
        #        um = np.array(list(density[serie]['u'].values()))
        #        ub = np.array(list(density[serie]['ub'].values()))

        #        # the twist averaging
        #        um = um.mean(0)
        #        ub = np.sqrt(sum([ x**2 for x in ub ]))


        #        # this is for writing to cube only
        #        # linearize prior to padding
        #        um = um.reshape(-1, 1)
        #        ub = ub.reshape(-1, 1)
        #        # for the weird *.cube 6-shape (same padlength for everything)
        #        padlength = 6 - um.shape[0] % 6
        #        um = np.append(um, np.zeros(padlength))
        #        ub = np.append(ub, np.zeros(padlength))
        #        # reshape
        #        um = um.reshape(-1, 6)
        #        ub = ub.reshape(-1, 6)
        #        #np.savetxt('qmc.'+serie+'.Density_u.cube', um, header=header, comments='')
        #        #np.savetxt('qmc.'+serie+'.Density_u-err.cube', um-ub, header=header, comments='')
        #        #np.savetxt('qmc.'+serie+'.Density_u+err.cube', um+ub, header=header, comments='')


    def get_cube_header(self):
        h00 = 'QMCPACK density/spin density data\nsource file: '+xmlfile+'\n'
        h1 = [ [x[0]]+x[1].tolist() for x in zip(self.grid, self.dr) ]
        h2 = [ y[0]+y[1].tolist() for y in zip(self.i, self.p) ]
        nat = len(h2)
        h0 = [[ nat, 0., 0., 0. ]]
        return h00+'\n'.join([ ' '.join([ str(y) for y in x ]) for x in h0+h1+h2 ])

    #def to_file(name=''):
    #    estimator = self.estimator
    #    header = get_cube_header()
    #    um = self.um
    #    ub = self.ub
    #    density = self.density()
    #    if estimator == 'density':
    #        for serie in density.keys():
    #            np.savetxt('qmc.'+serie+'.Density_u.cube', um, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.Density_u-err.cube', um-ub, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.Density_u+err.cube', um+ub, header=header, comments='')
    #    elif estimator == 'spindensity':
    #        for serie in density.keys():
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u.cube', um, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u-err.cube', um-ub, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u+err.cube', um+ub, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_d.cube', dm, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_d-err.cube', dm-db, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_d+err.cube', dm+db, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u+d.cube', um+dm, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u+d-err.cube', um+dm-udb, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u+d+err.cube', um+dm+udb, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u-d.cube', um-dm, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u-d-err.cube', um-dm-udb, header=header, comments='')
    #            np.savetxt('qmc.'+serie+'.SpinDensity_u-d+err.cube', um-dm+udb, header=header, comments='')


parser = argparse.ArgumentParser()
parser.add_argument('-e', type=int, default=0,
        help='Equillibration length')
parser.add_argument('-i', required=True,
        help='XML input file, used to get the cell geometry')
parser.add_argument('f', nargs='+',
        help='Density *stat.h5 files. Automatically twist averaged')
args = parser.parse_args()

xmlfile = args.i
scalarfiles = args.f
e = args.e

cell = ScalarField(xmlfile, scalarfiles, e)
estimator = cell.estimator
header = cell.get_cube_header()
cell.to_file()


# TODO: useless?
#ndens = len(scalarfiles)
#if ndens > 0:
#    outtype='avg'
#else:
#    outtype=''

# divide per series
# TODO: perhaps a general format for density is better

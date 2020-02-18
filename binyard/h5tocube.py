#!/usr/bin/env python
# actually h5 to cube

import h5py
import argparse
import numpy as np
from lxml import etree
from numpy.linalg import norm

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


# TODO: should not return in string; a dedicated data structure is better
# TODO: better variable naming
def cubexmlheader(xmlfile):
    """ Parse grid information from QMCPACK's XML """
    tree = etree.parse(xmlfile)
    h00 = 'QMCPACK density/spin density data\nsource file: '+xmlfile+'\n'

    for lattice in tree.xpath("///parameter[@name='lattice']"):
        l = np.array(list(map(float, lattice.text.split())))
        l = l.reshape(-1, 3)
    nl = [ norm(x) for x in l ]

    estimator = esttype(xmlfile)
    if estimator == 'spindensity':
        for _ in tree.xpath("///parameter[@name='dr']"):
            dr = [ float(x) for x in _.text.split() ]
            # because it is rounded up for integer grid
            grid = [ int(np.ceil(x[0]/x[1])) for x in zip(nl,dr) ]
            dr = [ x[0]/x[1] for x in zip(l, grid) ]
        try:
            grid
        except NameError:
            for _ in tree.xpath("///parameter[@name='grid']"):
                grid = _.text.split()
                dr = [ x[0]/x[1] for x in zip(l, grid) ]
        h1 = [ [x[0]]+x[1].tolist() for x in zip(grid, dr) ]
    elif estimator == 'density':
        for _ in tree.xpath("//estimator[@type='density']"):
            delta = np.array([ float(x) for x in _.get('delta').split() ])
            grid = [ int(x) for x in 1/delta ]
            dr = [ x[0]/x[1] for x in zip(l, grid) ]
        h1 = [ [x[0]]+x[1].tolist() for x in zip(grid, dr) ]

    for positions in tree.xpath("//attrib[@name='position']"):
        p = np.array(list(map(float, positions.text.split())))
        p = p.reshape(-1, 3)
        # remember that the positions are in fractional coordinates
        p = [ sum([ y[0]*y[1] for y in zip(x,l) ]) for x in p ]
    for ionid in tree.xpath("//attrib[@name='ionid']"):
        i = [ atomid[x.strip('0123456789')] for x in ionid.text.split() ]
        i = [ [x,x] for x in i ]
    h2 = [ y[0]+y[1].tolist() for y in zip(i,p) ]
    nat = len(h2)
    h0 = [[ nat, 0., 0., 0. ]]
    return h00+'\n'.join([ ' '.join([ str(y) for y in x ]) for x in h0+h1+h2 ])


parser = argparse.ArgumentParser()
parser.add_argument('-e', help='Equillibration length', type=int, default=0)
parser.add_argument('-i', help='QMCPACK input XML', required=True)
parser.add_argument('f', help='Estimator *.stat.h5 files', nargs='+')
args = parser.parse_args()

header = cubexmlheader(args.i)
estimator = esttype(args.i)
e = args.e

ndens = len(args.f)

if ndens > 0:
    outtype='avg'
else:
    outtype=''

# divide per series
density = {}
if estimator == 'spindensity':
    for h5file in args.f:
        f = h5py.File(h5file, 'r')
        u = f['Density']['u']['value'][e:]
        d = f['Density']['d']['value'][e:]
        series = h5file.split('.')[2]
        twist = h5file.split('.')[0].split('-')[-1]
        density.setdefault(series, {})
        density[series].setdefault('u', {})
        density[series].setdefault('ub', {})
        density[series].setdefault('d', {})
        density[series].setdefault('db', {})
        density[series]['u'][twist] = u.mean(0)
        density[series]['ub'][twist] = u.std(0)
        density[series]['d'][twist] = d.mean(0)
        density[series]['db'][twist] = d.std(0)

    for serie in density.keys():
        um = np.array(list(density[serie]['u'].values()))
        ub = np.array(list(density[serie]['ub'].values()))
        dm = np.array(list(density[serie]['d'].values()))
        db = np.array(list(density[serie]['db'].values()))

        # the twist averaging
        um = um.mean(0)
        dm = dm.mean(0)
        ub = np.sqrt(sum([ x**2 for x in ub ]))
        db = np.sqrt(sum([ x**2 for x in db ]))
        udb = np.sqrt(sum([ x**2 for x in [ub,db] ]))
        # for the weird *.cube 6-shape (same padlength for everything)
        padlength = um.shape[0] % 6
        um = np.append(um, np.zeros(padlength))
        dm = np.append(dm, np.zeros(padlength))
        ub = np.append(ub, np.zeros(padlength))
        db = np.append(db, np.zeros(padlength))
        udb = np.append(udb, np.zeros(padlength))
        # reshape
        um = um.reshape(-1, 6)
        dm = dm.reshape(-1, 6)
        ub = ub.reshape(-1, 6)
        db = db.reshape(-1, 6)
        udb = udb.reshape(-1, 6)
        np.savetxt('qmc.'+serie+'.SpinDensity_u.cube', um, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u-err.cube', um-ub, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u+err.cube', um+ub, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_d.cube', dm, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_d-err.cube', dm-db, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_d+err.cube', dm+db, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u+d.cube', um+dm, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u+d-err.cube', um+dm-udb, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u+d+err.cube', um+dm+udb, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u-d.cube', um-dm, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u-d-err.cube', um-dm-udb, header=header, comments='')
        np.savetxt('qmc.'+serie+'.SpinDensity_u-d+err.cube', um-dm+udb, header=header, comments='')
elif estimator == 'density':
    for h5file in args.f:
        f = h5py.File(h5file, 'r')
        u = f['Density']['value'][e:]
        series = h5file.split('.')[2]
        twist = h5file.split('.')[0].split('-')[-1]
        density.setdefault(series, {})
        density[series].setdefault('u', {})
        density[series].setdefault('ub', {})
        density[series]['u'][twist] = u.mean(0)
        density[series]['ub'][twist] = u.std(0)

    for serie in density.keys():
        um = np.array(list(density[serie]['u'].values()))
        ub = np.array(list(density[serie]['ub'].values()))

        # the twist averaging
        um = um.mean(0)
        ub = np.sqrt(sum([ x**2 for x in ub ]))
        # linearize prior to padding
        um = um.reshape(-1, 1)
        ub = ub.reshape(-1, 1)
        # for the weird *.cube 6-shape (same padlength for everything)
        padlength = 6 - um.shape[0] % 6
        um = np.append(um, np.zeros(padlength))
        ub = np.append(ub, np.zeros(padlength))
        # reshape
        um = um.reshape(-1, 6)
        ub = ub.reshape(-1, 6)
        np.savetxt('qmc.'+serie+'.Density_u.cube', um, header=header, comments='')
        np.savetxt('qmc.'+serie+'.Density_u-err.cube', um-ub, header=header, comments='')
        np.savetxt('qmc.'+serie+'.Density_u+err.cube', um+ub, header=header, comments='')

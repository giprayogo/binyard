#!/usr/bin/env python
import os
import shlex
import numpy as np
import subprocess
from subprocess import Popen,PIPE

qmca = '/mnt/lustre/applications/qmcpack/nexus/executables/qmca'
#some sort of struct of arrays
class Averaged:
    def __init__(self, fu=None):
        """Initialize Averaged = oh this is rubbish
           fu = formula units per unit cell
           """
        self.path, self.sup, self.e, self.eb, self.v,\
            self.vb, self.ee, self.eeb, self.mpc, self.mpcb,\
            self.tw = ([] for i in range(11))
        #Default to per supercell
        self.fu = 1 if fu is None else fu
    def append(self, inputlist):
        """append each arrays by value in arrays(rubbish)
           note that the path must be in the format of "XXX-S[supercell_size]"
        """
        self.path.append(inputlist[0])
        self.sup.append(int(inputlist[0].split('-')[1].replace('S','')))
        self.tw.append(int(inputlist[0].split('-')[0][0]))
        self.e.append   (inputlist[1])
        self.eb.append  (inputlist[2])
        self.v.append   (inputlist[3])
        self.vb.append  (inputlist[4])
        self.ee.append  (inputlist[5])
        self.eeb.append (inputlist[6])
        self.mpc.append (inputlist[7])
        self.mpcb.append(inputlist[8])
    def get_corrected_energy(self):
        """Return list of tuple of directories and their E+E_MPC-E_EE"""
        npe = np.array(self.e).astype(np.float)
        npeb = np.array(self.eb).astype(np.float)
        npee = np.array(self.ee).astype(np.float)
        npeeb = np.array(self.eeb).astype(np.float)
        npmpc = np.array(self.mpc).astype(np.float)
        npmpcb = np.array(self.mpcb).astype(np.float)
        npsup = np.array(self.sup).astype(np.float)
        corr = (npe + npmpc - npee) / npsup / self.fu
        corrb = np.sqrt(npeb**2 + npmpcb**2 + npeeb**2) / npsup / self.fu
        return zip(self.sup,self.tw,corr,corrb)
    def get_norm_energy(self):
        """Return list of energies and errorbars, normalised to f.u. per unit cell"""
        npe = np.array(self.e).astype(np.float)
        npeb = np.array(self.eb).astype(np.float)
        npsup = np.array(self.sup).astype(np.float)
        e = npe / npsup / self.fu
        eb = npeb / npsup / self.fu
        return zip(self.sup,self.tw,e,eb)
    def get_mpc_corr(self):
        npmpc = np.array(self.mpc).astype(np.float)
        npmpcb = np.array(self.mpcb).astype(np.float)
        npee = np.array(self.ee).astype(np.float)
        npeeb = np.array(self.eeb).astype(np.float)
        npsup = np.array(self.sup).astype(np.float)
        corr = (npmpc - npee) / npsup / self.fu
        corrb = np.sqrt(npmpcb**2 + npeeb**2) / npsup / self.fu
        mpc = npmpc / npsup / self.fu
        invsup = 1 / np.array(self.sup).astype(np.float)
        return sorted(zip(invsup,self.tw,corr,corrb), key=lambda x: x[1])

#The dir format: vmc-supertwist[TWIST_SIZE]-supershift[TWIST_GRID_SHIFT]-S[SUPERCELL_SIZE]
data = Averaged(fu=6)
paths = sorted(sorted([ path for path in os.listdir('.') if 'vmc-supertwist' in path ],\
                      key=lambda path: int(path.split('-')[1].replace('supertwist',''))),\
               key=lambda path: int(path.split('-')[3].replace('S','')))
print '#Path LocalEnergy +/- Variance +/- Electron-Electron +/- MPC +/-'
for path in paths:
    def rel(x): return os.path.join(path,x)
    scalar_files = [ rel(filename) for filename in os.listdir(path) if filename.endswith('scalar.dat') ]
    qmca_ev = shlex.split(qmca+' -e 2 -q ev --sac -a '+' '.join(scalar_files))
    qmca_ee = shlex.split(qmca+' -e 2 -q ee --sac -a '+' '.join(scalar_files))
    qmca_mpc = shlex.split(qmca+' -e 2 -q mpc --sac -a '+' '.join(scalar_files))
    ev,ee,mpc = ( subprocess.Popen(x,stdout=PIPE) for x in (qmca_ev,qmca_ee,qmca_mpc) )
    #Skip header of qmca output
    ev_out,ee_out,mpc_out = ( x.communicate()[0].decode('utf-8').split('\n')[y].split()\
                              for x,y in zip([ev,ee,mpc],[1,0,0]) )
    #Make it in the format of '[TWIST_SIZE]-S[SUPERCELL_SIZE]
    def trim(x): return x[-3:] if x.startswith('supertwist') else x
    try:
        ev_out[0] = '-'.join([ trim(path.split('-')[i]) for i in (1,3) ])
    except IndexError:
        print os.path.basename(__file__)+': No scalar.dat in '+path
        pass
    print '  '.join(ev_out)
    try:
        thing = [ ev_out[i] for i in (0,3,5,7,9) ]+[ ee_out[i] for i in (5,7) ]+[ mpc_out[i] for i in (5,7) ]
        data.append(thing)
    except IndexError:
        pass
print '\n\n#MPC corrected energies\n#S T MPCCorrectedEnergy +/-'
for datapoint in data.get_corrected_energy():
    print ' '.join(map(str,datapoint))
print '\n\n#Norm energies\n#S T LocalEnergy(f.u.) +/-'
for datapoint in data.get_norm_energy():
    print ' '.join(map(str,datapoint))
print '\n\n#MPC correction\n#S T LocalEnergy(f.u.) +/-'
for datapoint in data.get_mpc_corr():
    print ' '.join(map(str,datapoint))

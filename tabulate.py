#!/usr/bin/env python
#Generic tabulate of everything (jobs, outputs)

#python standard modules
import os
import sys
import shlex
import numpy as np
import subprocess
from subprocess import Popen,PIPE
import argparse
#modules from this module
import fileio

#all defs
qmca = '/mnt/lustre/applications/qmcpack/nexus/executables/qmca'
hostname = { 'cx250':'hpcc',
             'vpcc' :'vpcc',
             'xc40' :'xc40',
             'hster':'hster',
             'altix':'altix'
           }
status_string = { 'R':'running',
                  'F':'!!!---finished---!!!',
                  'H':'halted',
                  'Q':'in queue',
                  'E':'exiting',
                  'completed':'completed',
                  'pending':'PENDING/OLD',
                  'setup':'SETUP'
                }
#Files that needs to be available in order to be classified as "setup"
minimum_file = { 'casino'  :['?wfn.data*','input'],
                 'espresso':['input.in','*.upf'],   #Assuming standard unified format
                 'espresso_setupqmc':['*-scf.in'],
                 'vasp':['INCAR','POSCAR','KPOINTS']
               }
#Submitted jobs marker
marker_file = { 'subbed'   :['*.jss','JobNumber','UserName'],
                'completed':['COMPLETED']
              }
#Command line argument parsing
parser = argparse.ArgumentParser(description='Tabulate specified quantitities'
                                 ' in a format ready for further processing')
parser.add_argument('-q', '--qmca', type=int, metavar='FU_PER_CELL',
                    help="Do qmca -q ev,ee,mpc internally, with specified number of formula unit")
parser.add_argument('-j', '--jobs', action='store_true',
                    help="List jobs under current or [FILE] dir")
parser.add_argument('-e', '--energy', action='store_true',
                    help="get energies from output files under [FILE] (unimplemented)")
parser.add_argument('-p', '--program', type=str,
                    help="Specify calculation software used (default: all, unimplemented)")
parser.add_argument('FILE', default='.', nargs='?', help="UNIX idea of a file. i.e. root directory for search")

def main():
    #Do something
    args = parser.parse_args()
    program = 'all'
    if args.program:
        program = args.program #should be an array
    if args.qmca:
        qmca_energies('vmc-supertwist',args.qmca,args.FILE)
    if args.jobs:
        job(args.FILE)
    exit()
#=====Job listing=====
def job(path):
    file_list = ['*.jss', 'JobNumber', 'UserName'] #sub'd
    jobs = []
    dirlist = [ dir #TODO: make a tuple of dir and program type
                for k,v in minimum_file.iteritems() #if k in
                for dir in fileio.listdirwith(path,v) ]
    for path in dirlist:
        def test(file_list):
            for marker in file_list:
                if not marker in os.listdir(path):
                    return False
            return True
        if test(marker_file['completed']):
            jobs.append((path,status_string['completed']))
            continue
        try:
            jobnumber_file = open(os.path.join(path,'JobNumber'), 'r')
            jobnumber = jobnumber_file.read().rstrip('\n')
        except IOError:
            #err = sys.argv[0] + ": cannot access " + os.path.join(path,'JobNumber') + ": No such file"
            jobs.append((path,status_string['setup']))
            continue
            #sys.exit(err)
        try:
            username_file = open(os.path.join(path,'UserName'), 'r')
            username = username_file.read().rstrip('\n')
        except IOError:
            #err = sys.argv[0]+": cannot access "+os.path.join(path,'UserName')+": No such file"
            jobs.append((path,status_string['setup']))
            continue
            #sys.exit(err)
        #TODO: do it better
        cluster = [ f.split('.')[0] for f in os.listdir(path) if '.jss' in f ]
        qstat_comm = shlex.split('ssh '+username+'@'+hostname[cluster[0]]+' qstat -xf '+jobnumber)
        qstat = subprocess.Popen(qstat_comm,stdout=PIPE,stderr=PIPE)
        qstat_out = qstat.communicate()
        if 'Unknown Job Id' in qstat_out[1]:
        #if 'Unknown Job Id' in qstat_out[1]:
            jobs.append((path,status_string['pending']))
        elif 'cannot connect' in qstat_out[1]:
            jobs.append((path,status_string['pending']))
        else:
            pbs_var = fileio.fromstring_pbs(qstat_out[0])
            #bash_var = fileio.fromstring_bash(pbs_var['Variable_List'])
            #print pbs_var['job_state']
            #print bash_var['PBS_O_WORKDIR']
            jobs.append((path,status_string[pbs_var['job_state']]))
    jobs.sort(key=lambda a: a[1])
    for job in jobs:
        print(job)


#=====QMCPACK related=====
class Averaged:
    """Related to substraction or addition of qmca read properties"""
    def __init__(self, fu=None):
        """Initialize Averaged = oh this is rubbish
           fu = formula units per unit cell
           """
        self.path, self.sup, self.e, self.eb, self.v,\
            self.vb, self.ee, self.eeb, self.mpc, self.mpcb,\
            self.tw, self.line = ([] for i in range(12))
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
    def append_line(self, line):
        self.line.append(line)
    def get_line(self):
        return self.line
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

def qmca_energies(dir_match, fu=1,root='.'):
    """Obtain relevant energy quantities with qmca"""
    """Equivalent to doing qmca -q ev, ee, mpc on first sub of current directory"""
    #TODO: tidy up
    data = Averaged(fu)
    #The dir format: vmc-supertwist[TWIST_SIZE]-supershift[TWIST_GRID_SHIFT]-S[SUPERCELL_SIZE]
    paths = sorted(sorted([ os.path.join(root,path)
                            for path in os.listdir(root) if dir_match in path ],\
                          key=lambda path: int(path.split('-')[1].replace('supertwist',''))),\
                   key=lambda path: int(path.split('-')[3].replace('S','')))
    #print('#Path LocalEnergy +/- Variance +/- Electron-Electron +/- MPC +/-')
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
            print(os.path.basename(__file__)+': No scalar.dat in '+path)
            continue
        #print('  '.join(ev_out))
        thing = [ ev_out[i] for i in (0,3,5,7,9) ]+[ ee_out[i] for i in (5,7) ]+[ mpc_out[i] for i in (5,7) ]
        data.append(thing)
        data.append_line('  '.join(ev_out))
    #TODO: do not overwrite existing file

    dat_all = open('dat-all.dat', 'w')
    dat_all.write('#Path LocalEnergy +/- Variance +/- Electron-Electron +/- MPC +/-'+"\n")
    for datapoint in data.get_line():
        dat_all.write(datapoint+"\n")
    dat_all.close()

    dat_mpc = open('dat-mpc.dat', 'w')
    dat_mpc.write('#MPC corrected energies\n#S T MPCCorrectedEnergy +/-'+"\n")
    for datapoint in data.get_corrected_energy():
        dat_mpc.write(' '.join(map(str,datapoint))+"\n")
    dat_mpc.close()

    dat_norm = open('dat-norm.dat', 'w')
    dat_norm.write('#Norm energies\n#S T LocalEnergy(f.u.) +/-'+"\n")
    for datapoint in data.get_norm_energy():
        dat_norm.write(' '.join(map(str,datapoint))+"\n")
    dat_norm.close()

    dat_mpc_dake = open('dat-mpc-dake.dat', 'w')
    dat_mpc_dake.write('#MPC correction\n#S T LocalEnergy(f.u.) +/-'+"\n")
    for datapoint in data.get_mpc_corr():
        dat_mpc_dake.write(' '.join(map(str,datapoint))+"\n")
    dat_mpc_dake.close()

if __name__ == "__main__": main()

#=====Copied from list_energies.py=====

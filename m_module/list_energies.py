#!/usr/bin/env python
# Script to get energy values from calculation outputs

import os
import sys
import numpy as np
import argparse
import fileio
import fnmatch

casino_run_files = ['input','correlation.data','?wfn.data*']
espresso_run_files = ['input.in','out.o']

#temporary fix
def uniform(x):
    for sub in x:
        if isinstance(sub, basestring):
            yield sub
        else:
            try:
                for item in sub:
                    yield item
            except TypeError:
                yield sub
def get_espresso_out_file(root):
   outfile = os.path.join(root,'out.o')
   if os.path.isfile(outfile):
       return outfile
def get_casino_dmc_out_file(root):
    def out_is_here(root):
        runtype = get_casino_keyword(os.path.join(root,'input'), 'runtype')
        if runtype == 'dmc_stats':
            return os.path.isfile(os.path.join(root,'out'))
    if out_is_here(root):
        return os.path.join(root,'out') 
    else:
        def file_is_dir(filename): return os.path.isdir(os.path.join(root,filename))
        def dir_is_saves(dirname): return (dirname.startswith('esio') or dirname.startswith ('sio'))
        dirs = filter(file_is_dir and dir_is_saves, os.listdir(root))
        dirs.sort(reverse=True)
        if dirs:
            #loop until find a directory with a energy output
            for dir in dirs:
                outfile = os.path.join(root,dir,'out')
                if os.path.isfile(outfile) and get_casino_dmc_energies(outfile):
                    return outfile

def get_casino_keyword(filename, keyword):
    return fileio.readlineswith(filename, keyword, lambda x: x.split()[2],)[0]
def get_casino_dmc_energies(outfile):
    nsamp = fileio.readlineswith(outfile,'Number of data points',lambda l: l.split()[-1],)
    energy = fileio.readlineswith(outfile,r'Total energy.*\+/-',lambda l: [l.split()[i] for i in (-3,-1)],)
    fin_energy = fileio.readlineswith(outfile,r'^(?=.*Total energy)(?=.*(Ewald|MPC))(?!.*\+/-).*',lambda l: l.split()[-1],)
    return nsamp+energy+fin_energy
def get_casino_vmc_energies(outfile,interaction):
   mul = 1
   if interaction == 'ewald_mpc': #With mpc you get twice amount of results
       mul *= 2
   def get_energy_and_bar(line): return [ line.split()[index] for index in 0,2 ]
   uncorrected = fileio.readlineswith(outfile,r'\+/-.*No correction',get_energy_and_bar,[np.nan]*2*mul)
   correlated = fileio.readlineswith(outfile,r'\+/-.*Correlation time',get_energy_and_bar,[np.nan]*2*mul)
   reblocked = fileio.readlineswith(outfile,r'\+/-.*On-the-fly',get_energy_and_bar,[np.nan]*2*mul)
   variance = fileio.readlineswith(outfile,r'Sample variance',lambda l: l.split()[-1],[np.nan]*mul)
   return uncorrected+correlated+reblocked+variance
def get_espresso_energies(filename):
    return fileio.readlineswith(filename,'!',lambda line: line.split()[-2],)

#Printing functions
#print pattern abstraction
#for casino_run_dir in casino_run_dirs:
#    out = get_casino_dmc_out_file(casino_run_dir)
#    if out:
#        e = get_casino_dmc_energies(out)
#        if e:
#            print casino_run_dir + ' ' + ' '.join(map(str, e))
def printlist(l0,fn0,fn1):
    for i0 in l0:
        i1 = fn0(i0)
        if i1:
            i2 = fn1(i1)
            if i2:
                flatten = [ item for item in uniform(i2) ]
                print i0 + ' ' + ' '.join(map(str, flatten))
def print_espresso(with_list=espresso_run_files,filename='out.o'):
    edirs = fileio.listdirwith('./', with_list)
    for espresso_dir in edirs:
        outfiles = fileio.find_file(espresso_dir,filename)
        for outfile in outfiles:
            e = get_espresso_energies(outfile)
            if e:
                print espresso_dir + ' ' + ' '.join(map(str,e))
def print_all():
    casino_run_dirs = fileio.listdirwith('./',casino_run_files)
    espresso_run_dirs = fileio.listdirwith('./',espresso_run_files)

    print '####CASINO-DMC-TOTAL-ENERGIES####\n#DIR NSAMP Ewald Ewald(+/-) MPC MPC(+/-) E EXK EX EK M MK'
    printlist(casino_run_dirs,get_casino_dmc_out_file,get_casino_dmc_energies)
    print '\n\n####CASINO-CIO-E-TOTAL-ENERGIES####\n#DIR UNCORRECTED (+/-) CORRELATED (+/-) REBLOCKED (+/-) VARIANCE'
    for casino_run_dir in casino_run_dirs:
        out = os.path.join(casino_run_dir,'cio','out')
        if os.path.isfile(out):
            interaction = get_casino_keyword(os.path.join(casino_run_dir,'cio','input'), 'interaction')
            if interaction == 'ewald':
                e = get_casino_vmc_energies(out, interaction)
                if e:
                    flatten = [item for item in uniform(e)]
                    print casino_run_dir + ' ' + ' '.join(map(str, flatten))
    print '\n\n####CASINO-CIO-M-TOTAL-ENERGIES####\n#DIR UNCORRECTED (+/-) UNCORRECTED_MPC (+/-) CORRELATED (+/-) CORRELATED_MPC (+/-) REBLOCKED (+/-) REBLOCKED_MPC (+/-) VARIANCE'
    for casino_run_dir in casino_run_dirs:
        out = os.path.join(casino_run_dir,'cio','out')
        if os.path.isfile(out):
            interaction = get_casino_keyword(os.path.join(casino_run_dir,'cio','input'), 'interaction')
            if interaction == 'ewald_mpc':
                e = get_casino_vmc_energies(out, interaction)
                if e:
                    flatten = [item for item in uniform(e)]
                    print casino_run_dir + ' ' + ' '.join(map(str, flatten))
    print '\n\n####CASINO-HFVMC-E-TOTAL-ENERGIES####\n#DIR UNCORRECTED (+/-) CORRELATED (+/-) REBLOCKED (+/-) VARIANCE'
    for casino_run_dir in casino_run_dirs:
        out = os.path.join(casino_run_dir,'hfvmc','out')
        if os.path.isfile(out):
            interaction = get_casino_keyword(os.path.join(casino_run_dir,'hfvmc','input'), 'interaction')
            if interaction == 'ewald':
                e = get_casino_vmc_energies(out, interaction)
                if e:
                    flatten = [item for item in uniform(e)]
                    print casino_run_dir + ' ' + ' '.join(map(str, flatten))
    print '\n\n####CASINO-HFVMC-M-TOTAL-ENERGIES####\n#DIR UNCORRECTED (+/-) UNCORRECTED_MPC (+/-) CORRELATED (+/-) CORRELATED_MPC (+/-) REBLOCKED (+/-) REBLOCKED_MPC (+/-) VARIANCE'
    for casino_run_dir in casino_run_dirs:
        out = os.path.join(casino_run_dir,'hfvmc','out')
        if os.path.isfile(out):
            interaction = get_casino_keyword(os.path.join(casino_run_dir,'hfvmc','input'), 'interaction')
            if interaction == 'ewald_mpc':
                e = get_casino_vmc_energies(out, interaction)
                if e:
                    flatten = [ item for item in uniform(e) ]
                    print casino_run_dir + ' ' + ' '.join(map(str, flatten))
    print '\n\n####PWSCF-TOTAL-ENERGIES####\n#DIR TOTEN'
    printlist(espresso_run_dirs,get_espresso_out_file,get_espresso_energies)
#deprecated
#def get_casino_dmc_energies(outfile):
#    contain_fin_energy = lambda line: 'Total energy' in line and\
#                                    ( '(Ewald)' in line or '(MPC)' in line ) and\
#                                      not '+/-' in line
#    get_energy_and_bar = lambda line: [ line.split()[index] for index in -3,-1 ]
#    get_energy = lambda line: [ line.split()[-1] ]
#    get_nsamp = lambda line: [ line.split()[-1] ]
#    nsamp = Rule(line_contain('Number of data points'),get_nsamp)
#    energy = Rule(line_contain('Total energy','+/-'),get_energy_and_bar)
#    fin_energy = Rule(contain_fin_energy,get_energy)
#    return fileio.get_from_file(outfile,nsamp,energy,fin_energy)
#def get_casino_vmc_energies(outfile,interaction):
#   mul = 1
#   if interaction == 'ewald_mpc':
#       mul *= 2
#   def get_energy_and_bar(line): return [ line.split()[index] for index in 0,2 ]
#   #uncorrected = Rule(line_contain('No correction','+/-'),get_energy_and_bar,[np.nan]*2*mul)
#   #correlated = Rule(line_contain('Correlation time','+/-'),get_energy_and_bar,[np.nan]*2*mul)
#   #reblocked = Rule(line_contain('On-the-fly','+/-'),get_energy_and_bar,[np.nan]*2*mul)
#   #variance = Rule(line_contain('Sample variance'),get_variance,[np.nan]*mul)
#   uncorrected = fileio.readlineswith(outfile,r'\+/-.*No correction',get_energy_and_bar,[np.nan]*2*mul)
#   correlated = fileio.readlineswith(outfile,r'\+/-.*Correlation time',get_energy_and_bar,[np.nan]*2*mul)
#   reblocked = fileio.readlineswith(outfile,r'\+/-.*On-the-fly',get_energy_and_bar,[np.nan]*2*mul)
#   variance = fileio.readlineswith(outfile,r'Sample variance',lambda l: l.split()[-1],[np.nan]*mul)
#   return uncorrected+correlated+reblocked+variance
#   #return fileio.get_from_file(outfile,uncorrected,correlated,reblocked,variance)

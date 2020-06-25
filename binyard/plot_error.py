#!/usr/bin/env python
# for all to often task: text data file, plot single column

import matplotlib
matplotlib.rc('axes.formatter', useoffset=False)
import matplotlib.pyplot as plt
import argparse
from numpy import arange
from numpy import loadtxt
from numpy import transpose

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file', required=True, nargs='+')
parser.add_argument('-d', '--domain-column')
parser.add_argument('-c', '--column', required=True)
parser.add_argument('-e', '--error-column', required=True)
args = parser.parse_args()

datafiles = args.file

fig, ax = plt.subplots()
for datafile in datafiles:
    column = int(args.column)
    data = transpose(loadtxt(datafile, comments='#', usecols=column))

    errorcolumn = int(args.error_column)
    errordata = transpose(loadtxt(datafile, comments='#', usecols=errorcolumn))

    try:
        domain_column = int(args.domain_column)
        domain = loadtxt(datafile, comments='#', usecols=domain_column)
    except TypeError:
        domain = arange(0, data.shape[-1])

    ax.errorbar(domain, data, yerr=errordata)

fig.tight_layout()
plt.show()

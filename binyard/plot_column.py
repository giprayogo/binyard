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
parser.add_argument('-c', '--columns', nargs='+', required=True)
args = parser.parse_args()

datafiles = args.file

fig, ax = plt.subplots()
for datafile in datafiles:
    columns = map(int, args.columns)
    data = transpose(loadtxt(datafile, comments='#', usecols=columns))

    try:
        domain_column = int(args.domain_column)
        domain = loadtxt(datafile, comments='#', usecols=domain_column)
    except TypeError:
        domain = arange(0, data.shape[-1])

    if len(data.shape) > 1:
        for _ in data:
            ax.plot(domain, _)
    else:
        ax.plot(domain, data)

fig.tight_layout()
plt.show()

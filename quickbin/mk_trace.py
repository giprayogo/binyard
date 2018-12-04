#!/usr/bin/env python
# trace qmcpack scalar.dat or dmc.dat
# TODO: [fixed, by choosing multiple input files] choose scalar/dmc
#       [done] choose which column (read first # line)
#       [fixed] use filename instead of series number
#       [fixed] scalar ordering is wrong (important for multiple series)
#       total rewrite with matplotlib
import os
import sys

import numpy as np
import re
#import matplotlib.pyplot as plt

scalars = None
quantities = None
qlist = {}
try:
    filenames = sys.argv[1:] if sys.argv[1:] else None
    # scalar: (filename, twist, series, dmc/scalar)
    def resolve(regex_match):
        if regex_match:
            return regex_match.group(0)
        return ''
    scalars = [ (path,
        resolve(re.search(r'tw[0-9]+',path)),
        resolve(re.search(r'\.s[0-9]+\.',path)).strip('.').strip('s'),
        #re.search(r'\.[a-z]\.dat',path)[0].strip('.dat').strip('.'))
        resolve(re.search(r'(\.[a-z]+)(?=\.dat)', path)).strip('.'))
            for path in os.listdir('.')
            for filename in filenames if filename in path ]
    scalars.sort(key=lambda x: x[2])
    scalars.sort(key=lambda x: x[1])
    if not scalars:
        raise StopIteration(','.join(sys.argv[1:])+' not found')
    # input file validation
    headers = []
    for scalar in scalars:
        with open(scalar[0]) as quantity_file:
            headers.append( [ line for line in quantity_file.readlines() if re.match("#.*", line) ] )
    # if input files are similar, should collapse to only single element
    set_of_quantities = set([ x for header in headers for x in header ])
    if len(set_of_quantities) == 1:
        quantities = [ quant for quant in re.split(r'\s+', list(set_of_quantities)[0]) if not '#' in quant ]
    else:
        raise StopIteration('Input files are not equal')
except StopIteration as si:
    print(sys.argv[0]+': '+repr(si))
    exit()
#except TypeError as te:
#    """ Occurs when trying to loop over None filenames """
#    print("Usage: sys.argv[0] FILENAMES")
#    print(sys.argv[0]+': '+repr(te))
#    exit()

# read energy or other quantities
quantity = int(input('Please choose quantity: {}'.format(' '.join([ '({}){}'.format(str(counter), item) for counter, item in enumerate(quantities) ]))))

# remember that this is already sorted
for scalar in scalars:
    data_file = scalar[0]
    twist = scalar[1]
    series = scalar[2]
    kind = scalar[3]
    try:
        qlist[twist].extend( [ line.split()[quantity]
            for line in open(data_file).readlines()
            if not '#' in line ] )
    except KeyError:
        qlist[twist] = []
        qlist[twist].extend( [ line.split()[quantity]
            for line in open(data_file).readlines()
            if not '#' in line ] )

# output file labeling
label = ''
label_list = []
# for consistent naming
# series and twists
series = sorted(set([ element[2] for element in scalars ]))
twists = sorted([ keyname for keyname in qlist.keys() ])
kinds = list(set([ element[3] for element in scalars ]))

label_list.extend(series)
label_list.extend(twists)
label_list.extend([quantities[quantity]])
# will only work if files are of the same kind
if len(kinds) == 1:
    label_list.extend(kinds)
else:
    raise StopIteration('More than two kinds of input files (not yet implemented)')
    exit()
label = '_'.join(label_list)

# x axis and listification
max_length = max([ len(qlist[key]) for key in qlist.keys() ])
x = list(np.arange(max_length))

squarelist = [ qlist[key] for key in sorted(qlist.keys()) ]
squarelist.insert(0,x)

# fill with nan for empty series
for sublist in squarelist:
    diff = max_length - len(sublist)
    if diff:
        sublist.extend([float('nan')] * diff)

# change column to row
squarelist = np.matrix.transpose(np.array(squarelist))


# header (line 1: column labels; line 2: quantity)
header = '#'
for key in sorted(qlist.keys()):
    print('twist:{} nline:{}'.format(key, len(qlist[key])))
    header += ' '+key

with open('dat_'+label+'.dat', 'w') as plotdatfile:
    plotdatfile.write(header+'\n')
    plotdatfile.write('#'+quantities[quantity]+'\n')
    for entry in squarelist:
        plotdatfile.write(' '.join(list(entry))+'\n')
  #plotdatfile.write(str((qlist)))
  #pickle.dump(qlist, plotdatfile)

#!/usr/bin/env python

import sys
import re
import argparse
from fractions import Fraction
from decimal import Decimal
from functools import reduce

parser = argparse.ArgumentParser()
parser.add_argument('filename')
parser.add_argument('-c', '--column', required=True)
parser.add_argument('-m', '--multiplier', required=True)
args = parser.parse_args()

# because the Fraction library does not support decimal denumerator things
def s2float(string):
    return reduce(lambda x,y: x/y, [ float(x) for x in string.split('/') ])

filename = args.filename
columns = list(map(int, args.column.split(',')))

# make more sense for the purpose
if 'c' in args.multiplier:
    multiplier = False
    multiplier_index = int(args.multiplier.replace('c',''))
else:
    multiplier = Decimal(s2float(args.multiplier))

#1/c0 is *1 *1/c0, c0 is a var
#split[column] = Decimal(split[column]#)



with open(filename, 'r') as data_file:
    for line in data_file.readlines():
        if not line.strip():
            print('')
        elif re.match(r'\s*#', line):
            print(line.rstrip())
        else:
            split = line.split()
            for column in columns:
                if multiplier:
                    split[column] = Decimal(split[column]) * multiplier
                else:
                    #split[column] = Decimal(split[column]) / Decimal(split[multiplier_index])
                    split[column] = Decimal(split[column]) * Decimal(split[multiplier_index])
            print(' '.join(map(str,split)))

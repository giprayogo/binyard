#!/usr/bin/env python

import sys
import re
from fractions import Fraction
from decimal import Decimal

try:
    filename = sys.argv[1]
    columns = list(map(int,sys.argv[2].split(',')))
except IndexError:
    print("Usage: () FILENAME COLUMN MULTIPLIER".format(sys.argv[0]))
    exit()

try:
    multiplier = Decimal(float(Fraction(sys.argv[3])))
except IndexError:
    print("Usage: () FILENAME COLUMN MULTIPLIER/DIVIDER_COLUMN_INDEX(c[idx])".format(sys.argv[0]))
    exit()
except ValueError:
    # perhaps is using some symbol
    multiplier = False
    # TODO: make a more geneal implementation
    multiplier_index = int(sys.argv[3].replace('c',''))


with open(filename, 'r') as data_file:
    for line in data_file.readlines():
        if not line.strip():
            print('')
        elif re.match('#', line):
            print(line.rstrip())
        else:
            split = line.split()
            for column in columns:
                if multiplier:
                    split[column] = Decimal(split[column]) * multiplier
                else:
                    split[column] = 1/Decimal(split[multiplier_index])
            print(' '.join(map(str,split)))

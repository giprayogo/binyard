#!/usr/bin/env python

import sys
import re
import argparse
from fractions import Fraction
from decimal import Decimal

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--filename', required=True)
parser.add_argument('-c', '--column', required=True)
parser.add_argument('-m', '--multiplier', required=True)
parsed = parser.parse_args()

try:
    filename = parsed.filename
    columns = list(map(int,parsed.column.split(',')))
except IndexError:
    print("Usage: () FILENAME COLUMN MULTIPLIER".format(sys.argv[0]))
    exit()

try:
    multiplier = Decimal(float(Fraction(parsed.multiplier)))
except IndexError:
    print("Usage: () FILENAME COLUMN MULTIPLIER/DIVIDER_COLUMN_INDEX(c[idx])".format(sys.argv[0]))
    exit()
except ValueError:
    # perhaps is using some symbol
    multiplier = False
    # TODO: make a more geneal implementation
    multiplier_index = int(parsed.multiplier.replace('c',''))


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

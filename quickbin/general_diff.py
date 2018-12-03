#!/usr/bin/env python

import sys
import math
from fractions import Fraction

try:
    filename = sys.argv[1]
    columns = list(map(int,sys.argv[2].split(',')))
    err_columns = list(map(int,sys.argv[3].split(',')))
except IndexError:
    #TODO: more general format
    print("Usage: () FILENAME COLUMN ERR_COLUMN".format(sys.argv[0]))
    exit()

with open(filename, 'r') as data_file:
    reference_data = {}
    for line in data_file.readlines():
        if '#' in line:
            print(line.rstrip())
            continue
        else:
            split = line.split()
            if not any(reference_data.values()):
                for column in columns:
                    reference_data[column] = float(split[column])
                for err_column in err_columns:
                    reference_data[err_column] = float(split[err_column])
            else:
                for column in columns:
                    split[column] = float(split[column]) - reference_data[column]
                for err_column in err_columns:
                    split[err_column] = math.sqrt(float(split[err_column])**2 + reference_data[err_column]**2)
                print(' '.join(map(str,split)))

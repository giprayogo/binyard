#!/usr/bin/env python

import math
import argparse
from fractions import Fraction

parser = argparse.ArgumentParser()
parser.add_argument('filename')
parser.add_argument('--column', '-c', required=True)
parser.add_argument('--error-column', '-e')
args = parser.parse_args()

filename = args.filename
columns = list(map(int, args.column.split(',')))
err_columns = list(map(int, args.error_column.split(','))) if args.error_column else None

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
                if err_columns:
                    for err_column in err_columns:
                        reference_data[err_column] = float(split[err_column])
                print('ref: ',' '.join(map(str,split)))
            else:
                for column in columns:
                    split[column] = float(split[column]) - reference_data[column]
                if err_columns:
                    for err_column in err_columns:
                        split[err_column] = math.sqrt(float(split[err_column])**2 + reference_data[err_column]**2)
                print(' '.join(map(str,split)))

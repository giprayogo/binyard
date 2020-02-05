#!/usr/bin/env python
# Very useful script because I know the DMC steps start from s005
import re
import sys
import argparse
#import numpy as np
import autorunner

@autorunner.dmc_dat()
def common(x):
    return x

# this style is not optimal but fine for now regardless
@autorunner.qmcpack_output()
def output_capturer(x):
    return x

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='*', default=common())
parser.add_argument('-e', '--equil', nargs='*', type=int, default=None)
args = parser.parse_args()
if not args.equil:
    args.equil = [0] * len(args.files)
assert len(args.files) == len(args.equil)

def resolve(regex_match):
    if regex_match:
        return regex_match.group(0)
    return ''

def sort_by_series(x):
    return resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s')


if __name__ == '__main__':
    # divide files by number of twists
    scalar = {}
    equil_scalar = {}
    for e, filename in zip(args.equil, args.files):
        twist = resolve(re.search(r'tw[0-9]+', filename))
        scalar.setdefault(twist, [])
        equil_scalar.setdefault(twist, [])
        scalar[twist].append(filename)
        equil_scalar[twist].append(e)

    # (TEMP) calculate the total of multiple runs
    qmcout = []
    for filename in output_capturer():
        # I don't think we need to separate since we need ALL values
        #twist = resolve(re.search(r'tw[0-9]+', filename))
        #qmcout.setdefault(twist, [])
        #qmcout[twist].append(filename)
        qmcout.append(filename)

    print(scalar)

    for twist in scalar.keys():
        filename_list = scalar[twist]
        eq_length_list = equil_scalar[twist]
        filename_list.sort(key=sort_by_series)
        out_name = re.sub(r'\.s[0-9]+\.', r'.s000.', filename_list[0])
        out_string = ''
        # dirty quick method
        with open(filename_list[0]) as header_ref: # separate the header
            out_string += header_ref.readlines()[0]
        for eq_length, filename in zip(eq_length_list, filename_list):
            with open(filename, 'r') as something:
                some_list = [ x.strip() for x in something.readlines() if not '#' in x ]
                some_list = some_list[eq_length:]
                out_string += '\n'.join(some_list).strip() + '\n'
        with open(out_name, 'w') as something:
            something.write(out_string)
        print("written to: "+out_name)

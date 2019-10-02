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
parsed = parser.parse_args()

def resolve(regex_match):
    if regex_match:
        return regex_match.group(0)
    return ''

def sort_by_series(x):
    return resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s')


if __name__ == '__main__':
    # divide files by number of twists
    scalar = {}
    for filename in parsed.files:
        twist = resolve(re.search(r'tw[0-9]+', filename))
        scalar.setdefault(twist, [])
        scalar[twist].append(filename)

    # (TEMP) calculate the total of multiple runs
    qmcout = []
    for filename in output_capturer():
        # I don't think we need to separate since we need ALL values
        #twist = resolve(re.search(r'tw[0-9]+', filename))
        #qmcout.setdefault(twist, [])
        #qmcout[twist].append(filename)
        qmcout.append(filename)

    print(scalar)
    #print(qmcout)
    #print([ len(qmcout[x]) for x in qmcout.keys() ])
    dmc_times = [ float(y.strip().split()[4])
        for x in qmcout
        for y in open(x, 'r').readlines()
        if 'QMC Execution time' in y ]
    mpi_ranks = [ y
        for x in qmcout
        for y in open(x, 'r').readlines()
        if 'Total number of MPI ranks' in y ]
    omp_threads = [ y
        for x in qmcout
        for y in open(x, 'r').readlines()
        if 'OMP 1st level threads' in y ]

    print('Total DMC time: {}'.format(dmc_time))

    for twist in scalar.keys():
        filename_list = scalar[twist]
        filename_list.sort(key=sort_by_series)
        out_name = re.sub(r'\.s[0-9]+\.', r'.s000.', filename_list[0])
        out_string = ''
        # dirty quick method
        with open(filename_list[0]) as header_ref:
            out_string += header_ref.readlines()[0]
        for filename in filename_list:
            with open(filename, 'r') as something:
                some_list = [ x.strip() for x in something.readlines() if not '#' in x ]
                out_string += '\n'.join(some_list).strip() + '\n'
        with open(out_name, 'w') as something:
            something.write(out_string)
        print("written to: "+out_name)

#!/usr/bin/env python

import os
import sys
import re
import textwrap
import argparse

import fileio


def grep_final_coordinates(open_file):
    """ Input open file handle and return match string """
    out_string = ''
    is_param = False
    is_vcrelax = False
    ending = False
    # because some files has weird newlines
    #for line in map(str.rstrip, open_file.readlines()):
    for line in open_file.readlines():
        if 'CELL_PARAMETERS' in line:
            is_vcrelax = True
            is_param = True
            ending = False
            out_string = '' # only get the latest coordinate
        if not is_vcrelax and 'ATOMIC_POSITIONS' in line:
            is_param = True
            ending = False
            out_string = '' # only get the latest coordinate
        if line.isspace() or 'End final coordinates' in line:
            if ending or 'End final coordinates' in line:
                is_param = False
                ending = False
            else:
                ending = True

        if is_param:
            #out_string += line+'\n'
            out_string += line if line.endswith('\n') else line+'\n'

    return out_string


def get_final_force_and_energy(output_file):
    content_string = output_file.read()
    total_force = re.compile(r'(?<=Total force \=).+')
    total_energy = re.compile(r'(?<=\!).+')
    final_force = total_force.findall(content_string)[-1].split()[0]
    final_energy = total_energy.findall(content_string)[-1].split()[3]
    return (final_force, final_energy)


def get_final_pwx_input(input_file, output_file):
    try:
        # get latest match
        final_coordinates = grep_final_coordinates(output_file)
    except AttributeError:
        raise
    param = fileio.parse('pwx', input_file)
    new_param = fileio.fromstring_pwx(final_coordinates)
    param['atomic_positions'] = new_param['atomic_positions']
    if param['calculation']['value'] == '\'vc-relax\'':
        param['cell_parameters'] = new_param['cell_parameters']
    return fileio.tostring_pwx(param)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('input', nargs='?', default='input.in')
    parser.add_argument('output', nargs='?', default='out.o')
    args = parser.parse_args()
    output_pathname   = args.output
    input_pathname    = args.input
    final_in_pathname = 'auto_final.in'

    ## Make final.in out of updated positions in output file
    try:
        with open(output_pathname, 'r') as output_file:
            try:
                final_input = get_final_pwx_input(input_pathname, output_file)
            except AttributeError as e:
                print("%s: %s" % (sys.argv[0], e))
                raise
    except IOError as e:
        print("%s: %s" % (sys.argv[0], e))
        raise
    with open(final_in_pathname, 'w') as fi_file:
        fi_file.write(final_input)

#!/usr/bin/env python
import re
import sys
import argparse
#import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='+')
parsed = parser.parse_args()

def resolve(regex_match):
    if regex_match:
        return regex_match.group(0)
    return ''

def sort_by_series(x):
    return resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s')


# divide files by number of twists
scalar = {}
for filename in parsed.files:
    twist = resolve(re.search(r'tw[0-9]+', filename))
    scalar.setdefault(twist, [])
    scalar[twist].append(filename)

print(scalar)

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
            some_list = [ x for x in something.readlines() if not '#' in x ]
            out_string += '\n'.join(some_list)
    with open(out_name, 'w') as something:
        something.write(out_string)
    print("written to: "+out_name)

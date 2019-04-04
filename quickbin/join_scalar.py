#!/usr/bin/env python
import re
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('files', nargs='+')
parsed = parser.parse_args()

def resolve(regex_match):
    if regex_match:
        return regex_match.group(0)
    return ''
grouped = {}
for filename in parsed.files:
    twist = resolve(re.search(r'tw[0-9]+', filename))
    try:
        grouped[twist].append(filename)
    except KeyError:
        grouped[twist] = []
        grouped[twist].append(filename)

def sort_by_series(x):
    return resolve(re.search(r'\.s[0-9]+\.', filename)).strip('.').strip('s')
for twist in grouped.keys():
    fn_list = grouped[twist]
    fn_list.sort(key=sort_by_series)
    out_name = re.sub(r'\.s[0-9]+\.', r'.s000.', fn_list[0])
    out_string = ''
    # dirty quick method
    with open(fn_list[0]) as header_ref:
        out_string += header_ref.readlines()[0]
    for fn in fn_list:
        with open(fn, 'r') as something:
            some_list = [ x for x in something.readlines() if not '#' in x ]
            out_string += '\n'.join(some_list)
    with open(out_name, 'w') as something:
        something.write(out_string)
    print("written to: "+out_name)

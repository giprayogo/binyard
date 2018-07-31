#!/usr/bin/env python
import re

filename = 'input.in'
#flags
in_block = None
card_flags = {'atomic_pos':None}

pwx_input = open(filename,'r')
content = pwx_input.readlines()
parsed = {}
for line in content:
    def setflag(key):
        for k,v in card_flags.iteritems():
            if k == key:
                card_flags[k] = True
            else:
                card_flags[k] = False
    #Control lines
    if 'ATOMIC_POSITIONS' in line:
        setflag('atomic_pos')
        parsed['ATOMIC_POSITIONS'] = [re.search('{.*}',line).group(0)]
        continue
    #Process
    if card_flags['atomic_pos']:
        parsed['ATOMIC_POSITIONS'].append(re.split('\s+(?!$)',line.strip()))
print parsed

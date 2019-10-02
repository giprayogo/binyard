#!/usr/bin/env python

from binyard.etcetera import input_until_correct
import matplotlib
import numpy as np
from numpy import loadtxt
import re

#gui_envs = ['GTKAgg','TKAgg','Qt4Agg','WXAgg']
#for gui in gui_envs:
#    try:
#        matplotlib.use(gui,warn=False, force=True)
#        from matplotlib import pyplot as plt
#        break
#    except:
#        continue

# as the name describes
# should be only optionally called when specific column was not selected
def select_cols(filename, separator):
    with open(filename, 'r') as fh:
        # the 0 index means, for legend_line, extract only the uppermost line;
        legend_line = [ x for x in fh.readlines() if re.match(r'\s*#', x) ][0].strip().strip('#')

    legends = legend_line.split(separator)
    legends_text = 'choose; first one will become x-axis: ' + ' '.join([ '{}){} '.format(nx, x) for nx, x in enumerate(legends) ]) + '\n'
    # I know it is not the most legible way to do it but I love the multiples closing parentheses
    acceptable_indices = list(map(str, list(range(0, len(legend_line.split(separator))))))
    def _ (user_input):
        accepted = False
        things = filter(None, re.split(r'\s*|,', user_input))
        for thing in things:
            # only accept if all things are true
            if thing in acceptable_indices:
                accepted = True
            else:
                accepted = False
        return accepted
    # note that input_until_correct returns unprocessed text user input
    cols = map(int, filter(None, re.split(r'\s*|,', input_until_correct(legends_text, _))))
    return cols


# also in mac, sometimes it is not clear which fonts can be chosen
def print_fonts():
    flist = matplotlib.font_manager.get_fontconfig_fonts()
    for fname in flist:
        print(fname)
        if not '/Library/Fonts/NISC18030.ttf' in fname:
            matplotlib.font_manager.FontProperties(fname=fname).get_name()


# only one ax object per filename!
# why this one is needed: automatically infer string data as xtics
# return x and the y-axises
# todo: somehow separate ax processing from this
def autotic_loadtxt(filename, cols=None, separator=';'):
    data = []
    tics = []
    if cols is None:
        cols = select_cols(filename, separator)
    # column-by-column to catch string columns
    for col in cols:
        try:
            data.append(loadtxt(filename, usecols=col, dtype=np.number))
        except ValueError:
            # TODO: more complex behaviour is expected (such as handling of multiple string columns),
            # but for now defaulting tex to xtics shall suffice
            # TODO: handle multiple string arrays
            tics = loadtxt(filename, usecols=col, dtype=np.character)
    data = np.array(data)

    return data, tics

#!/usr/bin/env python
# general_plotter for quick plotting

import argparse
# parse first since matplotlib takes a long time to load
parser = argparse.ArgumentParser()
parser.add_argument('column', nargs='+')
parser.add_argument('--string-data', '-s', nargs='+')
parser.add_argument('--xaxis', '-a', nargs='+')
parser.add_argument('--xlabel', '-x', type=str)
parser.add_argument('--ylabel', '-y', type=str)
parser.add_argument('--xtics-column', 't')
#parser.add_argument('--title', type=str)
arg = parser.parse_args()

import matplotlib
gui_envs = ['GTKAgg','TKAgg','Qt4Agg','WXAgg']
for gui in gui_envs:
    try:
        matplotlib.use(gui,warn=False, force=True)
        from matplotlib import pyplot as plt
        break
    except:
        continue

# list of fonts
#flist = matplotlib.font_manager.get_fontconfig_fonts()
#for fname in flist:
#    print(fname)
#    if not '/Library/Fonts/NISC18030.ttf' in fname:
#        matplotlib.font_manager.FontProperties(fname=fname).get_name()
import numpy as np
font = {'family': 'sans-serif',
        #'sans-serif': '/System/Library/Fonts/Helvetica.ttc'}
        'sans-serif': '/Library/Fonts/Skia.ttf'}
#font = fm.FontProperties(fname='/System/Library/Fonts/Helvetica.ttc')
#plt.rcParams['font.family'] = 'cursive'
plt.rc('font', **font)


def plot_single(data_file, xc):
    # load
    if arg.string_data:
        #str_data = np.loadtxt(data_file, usecols=(0, 1), dtype=str)
        str_data = np.loadtxt(data_file, usecols=arg.string_data, dtype=str)
    num_data = np.loadtxt(data_file, usecols=(2,3,4,5,6))

    if str_data:
        str_data = np.array([ x for x in sorted(str_data,
            key=lambda x: x[XC_COLUMN]) if x[XC_COLUMN] == xc ])
    num_data = np.array([ x  for _,x in sorted(zip(str_data[:, XC_COLUMN], num_data),
        key=lambda x: x[0]) if _ == xc ])

    if arg.xaxis:
        t = num_data
    else:
        t = np.arange(0, np.shape(num_data)[0])
    for column in arg.column:
        plt.plot(t, num_data[:, column])

    if str_data and arg.xtics_column:
        plt.xtics(t, str_data[:, arg.xtics_column])
    #plt.xticks(x, str_data[:, POS_COLUMN], **font)
    #plt.title(xc, **font)
    #plt.xticks(x, str_data[:, POS_COLUMN], fontproperties=font)
    #plt.title(xc, fontproperties=font)
    #plt.xticks(x, str_data[:, POS_COLUMN])
    #plt.title(xc)
    #plt.plot(x, num_data[:, E_COLUMN])

if __name__ == '__main__':
    #plt.subplot(2,1,1)
    plot_single(arg.files[0], 'pbe')
    #plt.subplot(2,1,2)
    #plot_single(arg.files[0], 'pz')
    plt.show()

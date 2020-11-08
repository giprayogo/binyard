#!/usr/bin/env python
import argparse
import subprocess
import sys
import os
from os.path import join
import time

import numpy as np

import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from concurrent.futures import as_completed, wait
from concurrent.futures import ALL_COMPLETED, FIRST_EXCEPTION

from functools import wraps, partial, reduce

import re
from fnmatch import fnmatch
from pprint import pprint

from lxml import etree

import sympy
from sympy.parsing.sympy_parser import parse_expr

import hashlib
import pickle
from braceexpand import braceexpand

import matplotlib
import matplotlib.pyplot as plt
matplotlib.rc('axes.formatter', useoffset=False)

# shared options
extbin = { 'extrapolate_tau': '/Users/maezono/currentCASINO/bin_qmc/utils/'
                              'intelmac-gcc-brew/extrapolate_tau' }
subproc_opts = { 'capture_output': True }
HARTREE2RY = 2.

# TODO: can a generalized form be conceived for any kind of binary?
def extrapolate(data, save_filename, dfn, cfn, cefn=None, order=2, plot=False,
        xlabel='', ylabel='', title=''):
    """ Calls CASINO's extrapolate_tau for polynomial extrapolation with
            estimated error bar.
        Note that only codomain error is supported.
        Explanation:
            data: Any form of a collection of data
            dfn: Function for getting extrapolation domain from data
            cfn: Function for getting extrapolation codomain from data
            order: Polynomial order
            plot: (blocking) plot of the extrapolation for debug """

    def to_meanbartuple(numstring):
        """ Get mean-bar tuple from this format: -195.5(7) """
        parenthesized = re.compile(r'(?<=\().*(?=\))')
        nonparenthesized = re.compile(r'.*(?=\()')
        multiplier = 0.1**len(nonparenthesized.search(numstring).group().split('.')[-1])
        return (float(nonparenthesized.search(numstring).group()),
                multiplier*float(parenthesized.search(numstring).group()))

    def to_function(fnstring):
        """ Get function coefficients from string """
        pass


    # make the domain and codomain for extrapolation
    print('data', data)
    domain = [ dfn(x) for x in data ]

    # Automatically reduces polynomial order if data length is insufficient
    if len(data) < order:
        print('WARNING: insufficient data for given polynomial order; reducing',
                file=sys.stderr)
        order = len(data)

    codomain = [ cfn(x) for x in data ]
    if cefn:
        codomain_error = [ cefn(x) for x in data ]

    temporaryfilename = 'temp'+str(time.time())
    # Write a file for extrapolate_tau. This is the only way it can read data
    with open(temporaryfilename, 'w') as f:
        for d,c,ce in zip(domain,codomain,codomain_error):
            f.write(' '.join(map(str, [d, c, ce]))+'\n')
    # write the data
    os.makedirs('extrapolate_data', exist_ok=True)
    with open(os.path.join('extrapolate_data', save_filename), 'w') as f:
        # TODO: allow no-cefn as well
        for m in zip(domain, codomain, codomain_error):
            f.write(" ".join(map(str, m))+'\n')

    # open process
    pipe = subprocess.Popen(extbin['extrapolate_tau'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            encoding='utf8')

    # feeds for the process STDIN
    polynomial = ' '.join(map(str, range(order)))
    extrapolate_feed = '\n'.join([temporaryfilename, str(order), polynomial])
    stdout = pipe.communicate(extrapolate_feed+'\n', timeout=10)
    stdoutlines = stdout[0].split('\n')

    # TODO: I think this can be generalized
    try:
        extrapolated = [ to_meanbartuple(x.split()[-1])
                for x in stdoutlines
                if 'DMC energy at zero time step' in x ][0]
        # note the space: remove leading and trailing spaces as well
        function = parse_expr(next(
            ( x.strip('y= ').replace('^', '**') for x in stdoutlines if 'y=' in x )))
        x = next(iter(function.free_symbols))
    except IndexError:
        # The call has failed for unknown issue
        return None
    except StopIteration:
        # For single point data (e.g. hydrogen finite size), no extrapolation possible
        print('Warning: irregular extrapolate_tau output', file=sys.stderr)
        return extrapolated
    finally:
        os.remove(temporaryfilename)

    # NOTE: these function only accepts sympy function for now
    def ssreg(fn, domain, codomain):
        ybar = np.mean(np.array(codomain))
        return sum( (fn.subs([(x, d)]) -  ybar)**2 for d in domain )

    def sstot(fn, codomain):
        ybar = np.mean(np.array(codomain))
        return sum( (y -  ybar)**2 for y in codomain )

    # sorted actually for plotting
    _domain, _codomain, _codomain_error = zip(*sorted(
            zip(domain, codomain, codomain_error), key=lambda x: x[0]))

    #print(sstot(function, _codomain))
    #print(sstot(function, _codomain))
    #print(sstot(function, _codomain))
    #exit()

    r_square = ssreg(function, _domain, _codomain) / sstot(function, _codomain)

    if plot:
        fig, ax = plt.subplots()
        # TODO: how to determine general range
        rightmost = 1.05*max(domain)
        subdomain = np.linspace(0, rightmost, 200)
        ax.set_xlim(left=0, right=rightmost)

        ax.errorbar(_domain, _codomain, yerr=_codomain_error,
                marker='o',  capsize=5)
        ax.plot(subdomain, [function.subs([(x, d)]) for d in subdomain], marker='')
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)

        # print the r square
        left, right = ax.get_xlim()
        bottom, top = ax.get_ylim()
        xloc = left + 0.7*(right-left)
        yloc = bottom + 0.1*(top-bottom)
        plt.text(xloc, yloc, f'R-squared = {r_square:0.4f}')

        plt.tight_layout()
        plt.show()

    # Let the caller determine what to do with the extrapolation result
    return extrapolated


def get_tsteps(qmcpack_xml_filename):
    """ Use lxml library to get timesteps from every qmc runs """
    tree = etree.parse(qmcpack_xml_filename)
    return [ float(x.text) for x in tree.xpath("//qmc/parameter[@name='timestep']") ]

def query_qmcpack_output(cwd):
    # done like this as a form of priority list
    output_filenames = [ x for x in os.listdir(cwd) if fnmatch(x, '*.qmc') ]
    if not output_filenames:
        output_filenames = [ x for x in os.listdir(cwd) if fnmatch(x, '*:*.out') ]
        if not output_filenames:
            output_filenames = [ x for x in os.listdir(cwd) if fnmatch(x, '*.out') ]
            if not output_filenames:
                output_filenames = [ x for x in os.listdir(cwd) if fnmatch(x, '*.output') ]
                if not output_filenames:
                    return None # basically not run yet
    return output_filenames

def get_ln(filename, ln, cwd):
    """ get filename from wc """
    _ = subprocess.run(['wc', '-l', filename], cwd=cwd, **subproc_opts)
    ln[filename] = _.stdout.split()[0]

def qmcpack_hash(cwd):
    """ Join QMCPACK DMC scalars, hash them to see if there are any changes
    To be used for feeding hashedcache() """
    join_scalar = '/Users/maezono/Dropbox/01backup/git-repos/binyard/binyard/join_scalar.py'
    joinscalar_outs = subprocess.run(join_scalar, cwd=cwd, **subproc_opts)

    # check if no changes
    dmcdats = [ x for x in os.listdir(cwd) if fnmatch(x, '*s000.dmc.dat') ]
    hashes = [ hashlib.sha256(open(join(cwd, x), 'rb').read()).hexdigest()
            for x in dmcdats ]
    return hashes

# NOTE: the function must have cwd arg
# NOTE: can the file extension be generalized?
#       YES; instead of direct file-creating hashes a more
#            generalized module can be created
def hashedcache(hashfn, cachedir='./.cache'):
    """ cache a function output, if the output of the hash function changes """
    HASHPICKLE = '.hpkl' # "hash pickle"
    POSTPICKLE = '.pkl' # "just pickle"
    def wrapper(function):
        def wrapped(*args, **kwargs):
            cwd = kwargs['cwd']
            basename = cwd.replace('/', '_')+function.__name__
            prepickle = join(cachedir, basename+HASHPICKLE)
            postpickle = join(cachedir, basename+POSTPICKLE)
            # TODO: I think operations below are not-thread-safe; consider other options
            try:
                os.mkdir(cachedir)
            except FileExistsError:
                pass
            #if not os.path.exists(cachedir):
            #    os.mkdir(cachedir)

            # compare saved and current hashes
            hashes = hashfn(cwd)
            try:
                with open(prepickle, 'rb') as f:
                    pickled_hashes = pickle.load(f)
            except OSError:
                print("No hash pickles: {}".format(prepickle))
                pickled_hashes = None

            # try load pickled data; if the prepickle matches
            if pickled_hashes == hashes:
                try:
                    with open(postpickle, 'rb') as f:
                        data = pickle.load(f)
                        return data
                except OSError:
                    print("No pickled data: {}".format(postpickle))
                    pass

            print("Hash updated ({}); updating cache".format(cwd))
            # the actual execution of original function
            data = function(*args, **kwargs)

            # Cache new pickles
            with open(prepickle, 'wb') as f:
                pickle.dump(hashes, f)
            with open(postpickle, 'wb') as f:
                pickle.dump(data, f)
            return data
        return wrapped
    return wrapper

@hashedcache(qmcpack_hash)
def get_qmcpack_stats(cwd):
    """ All metadata of a qmcpack runs, in a directory """

    # get the number of samples from the joined scalar file
    # includes all twists, sum for all twists
    zerozeros = [ x for x in os.listdir(cwd) if '000.dmc.dat' in x ]
    threads = []
    ln = { x: None for x in zerozeros }
    # TODO: new way of threading
    for zerozero in zerozeros:
        _thread = threading.Thread(target=get_ln, args=(zerozero, ln, cwd))
        threads.append(_thread)
        _thread.start()
    for thread in threads:
        thread.join()
    # minus one for minus header
    samples = sum([ int(x)-1 for x in ln.values() ])

    dirname = cwd.split('/')[-1].strip()
    # remove all alphabetic components
    alphabet = re.compile(r'[a-zA-Z]*')
    # format : ads-supertwist611-supershift100-S2-dt...-...
    splitnum = [ re.sub(alphabet, '', x) for x in dirname.split('-') ]
    supercell = int(splitnum[3])
    #twist = int(splitnum[1].rstrip('11'))
    twist = int(splitnum[1]) # just postprocess later
    try:
        timestep = float(splitnum[4])
    except IndexError: # no mark means this
        timestep = 0.0025
    output_filenames = query_qmcpack_output(cwd)
    # cores and execution times
    cores = []
    relevant_execs = []
    for output_filename in output_filenames:
        # cache into memory since it is used many times
        output_file = [ x for x in open(os.path.join(cwd, output_filename), 'r') ]
        if not output_file:
            print("WARNING: empty output file: {}".format(join(cwd, output_filename)),
                    file=sys.stderr)
            continue

        input_file = [ x.split()[-1] for x in output_file if 'Input XML' in x ]
        if not input_file:
            # normaly because of canceled run; or crashes
            print("WARNING: Irregular output file: {}".format(join(cwd, output_filename)),
                    file=sys.stderr)
            continue
        if len(input_file) > 1:
            print("WARNING: output file from a combined run in {}".format(cwd),
                    file=sys.stderr)
        input_file = input_file[0]

        # I assume there are no subsequent runs with varying timesteps; which is normally the case
        exectimes = [ float(x.split()[-2]) for x in output_file if 'QMC Execution time' in x ]

        # get used mpi process and openmp threads
        # WARNING: qmcpack 3.5.0 does not print the Total MPI ranks in this way
        mpis = [ int(x.split()[-1]) for x in output_file if 'Total number of MPI ranks' in x ]
        if not mpis:
            # specially for qmcpack 3.5.0
            mpis = [ int(x.split()[-1]) for x in output_file if 'MPI Nodes  ' in x ]
        omps = [ int(x.split()[-1]) for x in output_file if 'OMP 1st level threads' in x ]
        if not len(mpis) == len(omps):
            print(mpis, omps)
            print("WARNING: irregular output file in {}".format(cwd))
        if len(mpis) > 1:
            print("WARNING: output file from a combined run in {}".format(cwd), file=sys.stderr)
        # but anyway in any case take the last
        mpis = mpis[-1]
        omps = omps[-1]
        # assuming it is matched to the allocated resource
        _cores = mpis*omps

        # get only execution time of the current timestep;
        # qmcpack sometimes tried to accelerate equillibration by using
        # larget initial timestep
        tsteps = get_tsteps(os.path.join(cwd, input_file))

        if not len(tsteps) == len(exectimes):
            print("WARNING: not all exec times for all timesteps listed: {}".format(
                    join(cwd, output_filename)), file=sys.stderr)
            continue

        assert len(tsteps) == len(exectimes)
        exec_each_tsteps = { str(x): y for x,y in zip(tsteps, exectimes) }

        try:
            # "relevant" execution time; excluding initialization runs
             relevant_exec = exec_each_tsteps[str(timestep)]
        except KeyError:
             # no run data -- then can't quantify from here: continue to the next output file
             print("WARNING: no timestep data on {}".format(cwd), file=sys.stderr)
             relevant_exec = None
             cores = None
        #cores.append(_cores)
        #relevant_execs.append(relevant_exec)

        #nps = [ t/3600/c for t,c in zip(relevant_execs, cores) ]
    #TODO: something better lah
    labels = [ 'sample', 'supercell', 'twist', 'timestep' ]
    dats = [samples, supercell, twist, timestep ]
    data = { x:y for x,y in zip(labels, dats) }
    return data


@hashedcache(qmcpack_hash)
def get_qmcpack_energies(cwd) -> dict:
    """ Throw dmcdats into qmcpack; cache results; read from cache if exists.
        This is because qmca processing can be very slow with a lot of samples.
        Note that the caching is now handled by @hashedcache tag """
    python2 = '/Users/maezono/miniconda3/envs/py27_gen/bin/python'
    qmca = '/Users/maezono/Dropbox/01backup/git-repos/qmcpack/nexus/bin/qmca'

    # check if no changes
    dmcdats = [ x for x in os.listdir(cwd) if fnmatch(x, '*s000.dmc.dat') ]

    # interface with qmca
    qmcacols = {'energy': 6, 'bar': 8}
    qmcaproc = [ python2, qmca, '-q', 'ev', '-a' ] # '-e', '5000' ]
    qmcaproc.extend(dmcdats)
    completedprocess = subprocess.run(qmcaproc, cwd=cwd, **subproc_opts)
    output = completedprocess.stdout.split()
    #print(output)
    data = { x:float(output[qmcacols[x]]) for x in ['energy', 'bar'] }
    return data


def process_directory(cwd:str, *fns, label:str=None) -> list:
    """ Bundle function for single thread/process run on single directory
        Can be feed to Thread or Process.
        Supposedly general for any calc software,
        given the implemented datafn, statfn, and ppfn """
    return [ fn(cwd=cwd) for fn in fns ]


def qmcpack_process(data:list, name, plot=False) -> list:
    """ Hard-defined procedures for a typical QMCPACK data
        Note: per-system basis """
    # start by timestep extrapolation
    # separate by twist and supercell
    # the flow: merge extrapolate, merge extrapolate
    # TODO: instead of list of list there ought to be a better representation
    def separate(data:list, separator=None) -> list:
        """ Group data by separator output """
        labels = set([ separator(x) for x in data ])
        return [ [ m for m in data if separator(m) == label ]
                for label in labels ]

    def sum_dict(a, b):
        """ Sum dict a,b into c. Same-key values merged into a list """
        c = {}
        keyset = set(iter(a)).union(set(iter(b)))
        for key in keyset:
            va = a.setdefault(key)
            vb = b.setdefault(key)
            if not isinstance(va, list):
                va = [va]
            if not isinstance(vb, list):
                vb = [vb]
            c[key] = va + vb
        return c

    # timestep extrapolation
    # what is it below: do not mix data for different supercell and twist size
    separated = separate(data, separator=lambda x: (x['supercell'], x['twist']))
    _data = [] # TODO: avoid this pattern
    for part in separated:
        # extrapolate when using at least 2 timesteps
        if len(part) >= 2:
            # remember that they are also merged here
            print(part[0]['supercell'])
            print(part[0]['twist'])
            ext_result = extrapolate(part,
                    dfn=lambda x: x['timestep'],
                    cfn=lambda x: x['energy']/x['supercell'],
                    cefn=lambda x: x['bar']/x['supercell'],
                    plot=plot, order=3,
                    xlabel='DMC timestep (a.u.)',
                    ylabel='DMC energy / prim. cell (Ha)',
                    save_filename='ts_'+name+'_'+str(part[0]['supercell']),
                    title='')
            mergedpart = reduce(sum_dict, part)
            # TODO: functionalized, and to be less weird-ed
            mergedpart.setdefault('ts_ext', {})
            mergedpart['ts_ext']['energy'] = ext_result[0]
            mergedpart['ts_ext']['bar'] = ext_result[1]
            _data.append(mergedpart)
        else:
            _data.append(part)

    # supercell extrapolation. assumes single twist grid size / supercell
    # TODO: no checks for available supercell sizes
    ext_result = extrapolate(_data,
            # note: there should be a check for not-equal result
            dfn=lambda x: 1/(list(set(x['supercell']))[0]),
            cfn=lambda x: x['ts_ext']['energy'],
            cefn=lambda x: x['ts_ext']['bar'],
            xlabel='1/N',
            save_filename='fn_'+name,
            ylabel='DMC energy / prim. cell (Ha)',
            plot=plot, order=2)
    procdata = reduce(sum_dict, _data)
    return (procdata, ext_result)


if __name__ == '__main__':
    # download
    download_root = 'dmc_energies'
    # remember that *THIS* is the main control for which files are being downloaded
    rsync_opts = [ '-av', '--delete',
            '--include=*/', # make all directories
            '--include=*.dmc.dat', '--include=*.scalar.dat', # the DMC datas
            '--include=*.qmc', '--include=*.out', # output files
            '--include=*.output', '--include=*.xml', # output files (2)
            '--include=template',
            '--exclude=*' ] # exclude anything else
    SSH_WORKER = 5

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--plot', action='store_true')
    parser.add_argument('-n', '--no-sync', action='store_true')
    args = parser.parse_args()
    plot = args.plot
    nosync = args.no_sync

    # read remote sources
    # TODO: temporary hard-naming
    with open('remotes', 'r') as f:
        raws = [ x.split() for x in f.readlines() if not '#' in x ]
    labels = [ x[0] for x in raws ]
    sources = [ x[1] for x in raws ]
    source_endings = [ x.split('/')[-1] for x in sources ]

    # pre-create download dirs
    downloaddirs = [ join(download_root, label) for label in labels ]
    for downloaddir in downloaddirs:
        if not os.path.exists(downloaddir):
            os.makedirs(downloaddir)

    # download to label directory under download_root
    # limit worker number due to maximum ssh connections
    if not nosync:
        with ThreadPoolExecutor(max_workers=SSH_WORKER) as executor:
            futures = []
            # not using list comprehension for readability
            for source, destination in zip(sources, downloaddirs):
                print('Downloading from: {}'.format(source))
                rsync = ['rsync'] + rsync_opts + [ source, destination ]
                future = executor.submit(subprocess.run(rsync)) #, cwd=download_root), )
                futures.append(future)
            done, not_done = wait(futures, return_when=FIRST_EXCEPTION)

    # list downloaded paths under each label
    assert len(labels) == len(downloaddirs) == len(source_endings)
    #print(source_endings)
    #print([[ fnmatch(x.path.split('/')[-1],ending) for x in os.scandir(downloaddir) ]
    #print([[ (x.path.split('/')[-1],ending) for x in os.scandir(downloaddir) ]
        #for downloaddir,ending in zip(downloaddirs, source_endings) ])
    labeledpaths = [
            (label, [ x.path
                for x in os.scandir(downloaddir)
                if x.is_dir() and
                any([ fnmatch(x.path.split('/')[-1], ending) for ending in braceexpand(endings) ]) ] )
            for label, downloaddir, endings in zip(labels, downloaddirs, source_endings) ]

    data = { x: [] for x in labels }
    with ThreadPoolExecutor() as executor:
        futures = {
                executor.submit(process_directory, path,
                    get_qmcpack_energies, get_qmcpack_stats): label
                for label, paths in labeledpaths
                for path in paths }
        # the blocking part
        for future in as_completed(futures):
            label = futures[future]
            results = future.result()
            merged = reduce(lambda x,y: {**x, **y}, results)
            data[label].append(merged) #= future.result()

    final = {}
    # postprocessing of data
    for label, part in data.items():
        print(label)
        if plot:
            procdata, ext_result = qmcpack_process(part, plot=True, name=label)
        else:
            procdata, ext_result = qmcpack_process(part, plot=False, name=label)
        print(procdata)
        print(ext_result)
        final[label] = ext_result
    print(final)
    # temp: ugly "processing"
    print('Energy: {}'.format(final['cplx'][0] - final['bare'][0] - final['hyd'][0]))
    print('Bar: {}'.format((final['cplx'][1]**2 + final['bare'][1]**2 + final['hyd'][1]**2)**0.5))
    exit()


    # just for printing format
    def flex_format(_):
        if isinstance(_, int):
            return str(_)
        elif isinstance(_, float):
            return '{0: 5f}'.format(_)

    pprint(procdata)
    print([ x['extrapolated'] for x in procdata.items() ])

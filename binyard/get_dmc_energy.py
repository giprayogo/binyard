#!/usr/bin/env python
# script; very specific; for only this task
# thread spwasn another thread spawn another thread
# to be made into a general crawler
# TODO: can the pickle be made as a wrapper?
import argparse
import subprocess
import sys
import os
from os.path import join
import time

import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed, wait
from concurrent.futures import ALL_COMPLETED, FIRST_EXCEPTION

from functools import wraps, partial, reduce

import re
from fnmatch import fnmatch
from pprint import pprint

from lxml import etree

import hashlib
import pickle

# binaries and scripts
rsync = ['rsync']

# shared options
subproc_opts = { 'capture_output': True }
HARTREE2RY = 2.

# TODO: can a generalized form be conceived for any kind of binary?
def extrapolate(data, dfn, cfn, defn=None, cefn=None, flatfn=None, order=2):
    """ Calls in extrapolate_tau to calculate the data
    Signature: extrapolate(data, fn=lambda x:x, args=None, key='timestep', order=2)
        data: collection of data in any form you want; as long as you supply a correct function
        dfn: function to get domain
        cfn: function to get codomain
        order: polynomial order of the extrapolation
    And return in the form of original data, with merged properties """
    extrapolate_tau = '/Users/maezono/currentCASINO/bin_qmc/utils/intelmac-gcc-brew/extrapolate_tau'

    # make the domain and codomain for extrapolation
    d = [ dfn(x) for x in data ]
    if defn:
        de = [ defn(x) for x in data ]

    c = [ cfn(x) for x in data ]
    if cefn:
        ybars = [ cefn(x) for x in data ]

    temporaryfilename = 'temp'+str(time.time())
    # make a temporary file for the extrapolate_tau
    with open(temporaryfilename, 'w') as f:
        for t,y,ybar in zip(d,c,ybars):
            f.write(' '.join(map(str, [t, y, ybar]))+'\n')

    # open process
    pipe = subprocess.Popen(extrapolate_tau,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            encoding='utf8')

    # feeds for the process STDIN
    polynomial = ' '.join(map(str, range(order)))
    extrapolate_feed = '\n'.join([temporaryfilename, str(order), polynomial])
    stdout = pipe.communicate(extrapolate_feed+'\n', timeout=10)

    # this is very SPECIFIC to the extrapolate_tau binary
    extrapolated = [ to_meanbartuple(x.split()[-1]) for x in stdout[0].split('\n')
            if 'DMC energy at zero time step' in x ]

    # remove leftovers and return
    os.remove(temporaryfilename)
    if flatfn:
        return (flatfn(data), extrapolated)
    else:
        return (data, extrapolated)

def to_meanbartuple(numstring):
    """ Input string in this format: -195.5(7) """
    parenthesized = re.compile(r'(?<=\().*(?=\))')
    nonparenthesized = re.compile(r'.*(?=\()')
    multiplier = 0.1**len(nonparenthesized.search(numstring).group().split('.')[-1])
    return (float(nonparenthesized.search(numstring).group()),
            multiplier*float(parenthesized.search(numstring).group()))

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
    """ To be used to determine caching """
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
            if not os.path.exists(cachedir):
                os.mkdir(cachedir)

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
    alphabet = re.compile(r'[a-zA-Z]*')
    # format : ads-supertwist611-supershift100-S2-dt...-...
    splitnum = [ re.sub(alphabet, '', x) for x in dirname.split('-') ]
    supercell = int(splitnum[3])
    twist = int(splitnum[1].rstrip('11'))
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
    #return samples, supercell, twist, timestep, label

@hashedcache(qmcpack_hash)
def get_qmcpack_energies(cwd):
    """ Throw dmcdats into qmcpack; cache results; read from cache if exists.
        This is because qmca processing can be very slow with a lot of samples """
    python2 = '/Users/maezono/miniconda3/envs/py27_gen/bin/python'
    qmca = '/Users/maezono/Dropbox/01backup/git-repos/qmcpack/nexus/bin/qmca'
    #join_scalar = '/Users/maezono/Dropbox/01backup/git-repos/binyard/binyard/join_scalar.py'

    # caching
    #PREPICKLE = '.ppkl'
    #POSTPICKLE = '.qpkl'
    #basename = cwd.replace('/', '_').strip('_')
    #prepickle = join(cachedir, basename+PREPICKLE)
    #postpickle = join(cachedir, basename+POSTPICKLE)
    #if not os.path.exists(cachedir):
    #    os.mkdir(cachedir)

    # first merge the dmc files
    #joinscalar_outs = subprocess.run(join_scalar, cwd=cwd, **subproc_opts)

    # check if no changes
    dmcdats = [ x for x in os.listdir(cwd) if fnmatch(x, '*s000.dmc.dat') ]
    #hashes = [ hashlib.sha256(open(join(cwd, x), 'rb').read()).hexdigest()
    #        for x in dmcdats ]
    #try:
    #    with open(prepickle, 'rb') as f:
    #        pickled_hashes = pickle.load(f)
    #except OSError:
    #    print("No datafile pickles: {}".format(prepickle))
    #    pickled_hashes = None

    # try load pickled data; if the prepickle matches
    #if pickled_hashes == hashes:
    #    try:
    #        with open(postpickle, 'rb') as f:
    #            return pickle.load(f)
    #    except OSError:
    #        print("No pickled data: {}".format(postpickle))
    #        # Continue to executing qmca
    #        pass

    # interface with qmca
    qmcacols = {'energy': 6, 'bar': 8}
    qmcaproc = [ python2, qmca, '-q', 'ev', '-a', '-e', '5000' ]
    qmcaproc.extend(dmcdats)
    completedprocess = subprocess.run(qmcaproc, cwd=cwd, **subproc_opts)
    output = completedprocess.stdout.split()
    #try:
    data = { x:float(output[qmcacols[x]]) for x in ['energy', 'bar'] }

    # Cache new pickles
    #with open(prepickle, 'wb') as f:
    #    pickle.dump(hashes, f)
    #with open(postpickle, 'wb') as f:
    #    pickle.dump(data, f)

    return data
    #except ValueError as ve:
        # no qmca files' skip; miscellaneous qmca error
    #    return None
        #raise ValueError(ve)

# bundle function for single thread/process run on single directory
def process_directory(cwd:str,
        *fns, label:str=None) -> list:
        #datafn:function=lambda _: None, statfn:function=lambda _: None,
        #label:str=None) -> list:
    """ Each; single; (any software) run directory;
        consist of any data as defined by statfn.
        Can be feed to Thread or Process.
        Supposedly general for any calc software,
        given the implemented datafn, statfn, and ppfn """
    #stats = statfn(cwd=cwd)
    #data = datafn(cwd=cwd)
    return [ fn(cwd=cwd) for fn in fns ]
    #return (stats, data)
    # get combined dmc runs from the newer runs
    # out: 000.dat
    #print(joinscalar_outs.stderr, file=sys.stderr)

        # modify data
        # TODO: better integration of the label
        #labels = [ 'label', 'supercell', 'twist', 'timestep', 'energy', 'bar', 'samples',
        #        'cores', 'execution_time', 'nodehour per step' ]
        #things = [ label, supercell, twist, timestep, energy*HARTREE2RY/supercell,
        #        bar*HARTREE2RY/supercell, samples]
                #sum(cores)/len(cores), sum(relevant_execs)/len(relevant_execs),
                #sum(nps)/len(nps) ]
        #data[cwd] = { x: y for x,y in zip(labels, things) }
        #final = { x:y for x,y in zip(labels, things) }
        #print(final)
        #with open(picklename+'dat', 'wb') as f:
        #    pickle.dump(final, f)
        #return final

if __name__ == '__main__':
    # download
    root = 'dmc_energies'
    syslabels = [ 'cplx', 'bare' ]
    rsync_opts = [ '-av', '--delete',
            '--include=*/', '--include=*.dmc.dat', '--include=*.scalar.dat',
            '--include=*.qmc', '--include=*.out', '--include=*.output', '--include=*.xml',
            '--exclude=*' ]
    SSH_WORKER = 5

    # read remote sources
    # TODO: temporary hard-naming
    with open('remotes', 'r') as f:
        remote_sources = [ [x] for x in f if not '#' in x ]

    # pre-create dirs
    if not os.path.exists(root):
        os.mkdir(root)
    for path in syslabels:
        if not os.path.exists(join(root, path)):
            os.mkdir(join(root, path))

    # download both complex and bare
    # limit worker number due to maximum ssh connections
    with ThreadPoolExecutor(max_workers=SSH_WORKER) as executor:
        futures = [ executor.submit(
            subprocess.run(rsync + rsync_opts + source + [path], cwd=root), )
                for source, path in zip(remote_sources, syslabels) ]
        done, not_done = wait(futures, return_when=FIRST_EXCEPTION)

    # note: always transport full paths
    pathlists = [ [ os.path.join(root, subroot, path)
        for path in os.listdir(os.path.join(root, subroot)) ]
        for subroot in syslabels ]
    systems = {s: d for s,d in zip(syslabels, pathlists)}

    # initial postprocessing of data
    data = { x: [] for x in systems }
    with ThreadPoolExecutor() as executor:
        futures = {
                executor.submit(process_directory, path,
                    get_qmcpack_energies, get_qmcpack_stats): syslabel
                for syslabel,paths in systems.items()
                for path in paths }
        # this part is the blocking one
        for future in as_completed(futures):
            syslabel = futures[future]
            resultstuple = future.result()
            merged = reduce(lambda x,y: {**x, **y}, resultstuple)
            data[syslabel].append(merged) #= future.result()
    print(' '.join([ 'supercell', 'twist', 'timestep', 'energy', 'bar', 'samples',
            'cores', 'execution_time', 'nodehour per step' ]))

    # postprocessing of data
    # NOTE: divided by datatype
    procdata = {}
    for syslabel,results in data.items():
        def get_suptt(x):
            # omit timestep (because that is the one we would like to extrapolate)
            return (x['supercell'], x['twist'])
        supttpair = set([ get_suptt(x) for x in results ])
        sortedresults = [ [ m for m in results if get_suptt(m) == k ] for k in supttpair ]
        # extrapolate w.r.t. timestep

        def mergedict(a, b):
            """ Merge dict a to dict b, turn same key values into a list """
            c = {}
            keyset = set(iter(a)).union(set(iter(b)))
            for key in keyset:
                va = a.setdefault(key)
                vb = b.setdefault(key)
                c[key] = (va, vb)
            return c

        procdata[syslabel] = []
        for r in sortedresults:
            #print(r)
            if len(r) >= 2:
                extrapolated_pair = extrapolate(r,
                        dfn=lambda x: x['timestep'],
                        cfn=lambda x: x['energy']/x['supercell'],
                        cefn=lambda x: x['bar']/x['supercell'], order=2,
                        flatfn=partial(reduce, mergedict))
                # TODO: functionalized
                _ = extrapolated_pair[0]
                _['extrapolated'] = extrapolated_pair[1]
                procdata[syslabel].append(_)
            else:
                procdata[syslabel].append(r)

    # just for printing format
    def flex_format(_):
        if isinstance(_, int):
            return str(_)
        elif isinstance(_, float):
            return '{0: 5f}'.format(_)

    pprint(procdata)
    #pprint({ k: [ ' '.join([ str('{0:.4f}'.format(x)) for x in y.values() ]) for y in v ] for k,v in data.items() })
#    pprint(data)
#    pprint({ k: [ ' '.join([ flex_format(x) for z in y for x in z.values() ]) for y in v ] for k,v in data.items() })
    #print('\n'.join([ ' '.join([ str(x) for x in y[1] ]) for y in _data ]))


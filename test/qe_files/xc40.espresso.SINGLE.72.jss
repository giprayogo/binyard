#!/bin/bash
#PBS -q SINGLE
#PBS -j oe
#PBS -l select=2:ncpus=36:mpiprocs=36
#PBS -N d2

cd $PBS_O_WORKDIR

#cnt=$((2/2)) #fatal: if only 1 node -> npool = 0!
#cnt=2
#[ cnt -eq 0 ] && cnt=1

#VERSION 6.1.0 6.4-elpa
version=6.4-elpa

#set binary
[ -e binary  ] &&  binary=$(cat binary | tr -d '\n')  || binary='pw.x'
[ -e options ] && options=$(cat options | tr -d '\n')
#[ -e npool   ] &&     cnt=$(cat npool | tr -d '\n')
[ -e version ] && version=$(cat version | tr -d '\n') || { echo VERSION > version ; }

# setenv OMP_NUM_THREADS 1 #tcsh
export OMP_NUM_THREADS=1 #bash

# set turbo-RVB ROOT
#espresso=/work/maezono-group/applications_180828/espresso-$version/bin/${binary}
espresso=/work/maezono-group/applications/espresso-$version/bin/${binary}

# run the job
#print "aprun -n 72 -N 36 -d 1 -ss $espresso $options -npool $cnt -inp input.in > out.o"
#aprun -n 72 -N 36 -d 1 -ss $espresso $options -npool $cnt -inp input.in > out.o
echo "aprun -n 72 -N 36 -d 1 -ss $espresso $options -inp input.in > out.o"
aprun -n 72 -N 36 -d 1 -ss $espresso $options -inp input.in > out.o

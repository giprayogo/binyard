#!/bin/bash
# exec command (last arg) on each dir (other args)
# (for doing equivalent to e.g. tossall, fetchall)
# 2018/09/13: First composed by genki
[ -z "$1" ] && { echo "usage: ${0##*/} DIRECTORIES* COMMAND"; exit; }
for dir in "${@:1:(($#-1))}"
do
 cwd=$(pwd)
 cd $dir
  eval "${@: -1}"
 cd $cwd
done

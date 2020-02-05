#!/bin/bash
# exec command (last arg) on each dir (other args)
# (for doing equivalent to e.g. tossall, fetchall)
# 2019/10/6:  Change bash -i to bash since it wasn't correctly importing environment variables
# 2019/04/25: Change pattern for file handling; instead access filename from variable $file
# 2019/04/23: Use subshell by replacing eval with bash -c
# 2019/04/23: Finally found suitable implementation
# 2019/04/23: Revert to directory limit; some generalization is required for file operations
# 2019/04/23: Do not restrict to directories; file operations are sometimes desired
# 2018/09/13: First composed by genki
[ -z "$1" ] && { echo "usage: ${0##*/} FILES/DIRS* COMMAND"; exit; }
for file in "${@:1:(($#-1))}"
do
 [ -d $file ] && { cwd=$(pwd); cd $file; (eval "${@: -1}"); cd $cwd; }
 [ -f $file ] && { c=${@: -1}; (eval "${c//\{\}/$file}"); }
done

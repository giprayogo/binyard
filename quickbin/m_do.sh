#!/bin/bash -i
<<<<<<< HEAD
# exec command (last arg) on each dir (other args)
# (for doing equivalent to e.g. tossall, fetchall)
=======
# tossall, fetchall, -any-all replacement
# eval command (last arg) on each dir (other args)
# 2018/04/23: Use subshell by replacing eval with bash -c
# 2018/04/23: Finally found suitable implementation
# 2018/04/23: Revert to directory limit; some generalization is required for file operations
# 2018/04/23: Do not restrict to directories; file operations are sometimes desired
>>>>>>> cdf8d0f715f7748fb6bb5a005cee77b66a1db157
# 2018/09/13: First composed by genki
# sometime in April 19: directory only, make aliases work by using interactive -i
[ -z "$1" ] && { echo "usage: ${0##*/} FILES/DIRS* COMMAND"; exit; }
for file in "${@:1:(($#-1))}"
do
<<<<<<< HEAD
 [ -d $dir ] && { cwd=$(pwd); cd $dir; eval ${@: -1}; cd $cwd; }
=======
 [ -d $file ] && { cwd=$(pwd); cd $file; (eval "${@: -1}"); cd $cwd; }
 [ -f $file ] && (eval "${@: -1} $file")
>>>>>>> cdf8d0f715f7748fb6bb5a005cee77b66a1db157
done

#!/bin/sh
# 2018Feb02 ; Forked by genki (quite p** with the robustness)
#             allow multiple attempts (so that it will compile iff the selected file exists)
#             note: -e *.tex does NOT check for the existence of files ending with .tex
#rm *.aux *.dvi *.idx *.log *.toc *.bbl *.blg *.out
#have a breath
o=o
while true ; do
  if [ -z "$1" ]; then
    numtex=$(ls -l *.tex | wc -l)
    [ $numtex -gt 1 ] && [ $o ] && { echo "Available tex files:\n$(ls *.tex)"; o=''; }
    [ $numtex -eq 1 ] && target=$(ls *.tex) || { echo "Specify compiled TeX file name!"; read -r target; }
  else
    target="$1"; shift;
  fi
  [ -f "$target" ] && break || { echo "${0##*/}: $target: No such file"; target=""; }
done
echo "Compile target: $target"
target=${target%.tex}

PATH=/opt/local/bin/:$PATH
platex  -halt-on-error -interaction=nonstopmode --kanji=sjis $target || exit -1
pbibtex -halt-on-error -interaction=nonstopmode --kanji=sjis $target || exit -1
platex  -halt-on-error -interaction=nonstopmode --kanji=sjis $target || exit -1
pbibtex -halt-on-error -interaction=nonstopmode --kanji=sjis $target || exit -1
platex  -halt-on-error -interaction=nonstopmode --kanji=sjis $target || exit -1
dvipdfmx -halt-on-error -interaction=nonstopmode $target.dvi
#rm *~
open $target.pdf

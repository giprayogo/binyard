#!/bin/sh
# 2018Feb02 ; Modified by genki (as usual improved robustness)
#             allow multiple attempts (so that it will compile iff the selected file exists)
#             note: -e *.tex does NOT check for the existence of files ending with .tex
#rm *.aux *.dvi *.idx *.log *.toc *.bbl *.blg *.out
ha=ha
while true ; do
  if [ "$1" = "" ]; then
    numtex=$(ls -l *.tex | wc -l)
    [ $numtex -gt 1 ] && [ $ha ] && { ls *.tex; ha=''; }
    [ $numtex -eq 1 ] && target=$(ls *.tex) || { echo "Specify compiled TeX file name!"; read -r target; }
  else
    target="$1"; shift;
  fi
  [ -f "$target" ] && break || { echo "$0: $target: No such file"; target=""; }
done
echo $target
target=$(echo $target | sed 's/.tex//')

PATH=/opt/local/bin/:$PATH
#pdflatex --kanji=sjis $target
#pdflatex --kanji=sjis $target
platex --kanji=sjis $target
pbibtex --kanji=sjis $target
platex --kanji=sjis $target
pbibtex --kanji=sjis $target
platex --kanji=sjis $target
dvipdfmx $target.dvi
#rm *~
open $target.pdf

#!/usr/bin/env python
import sys

from pymatgen import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.io.cif import CifWriter

filename = sys.argv[1]
filename_half = filename.split('.')[0]
structure = Structure.from_file(filename)
#sganalyzer = SpacegroupAnalyzer(structure)
cifwriter = CifWriter(structure, symprec=1.0e-4)
cifwriter.write_file(f'{filename_half}-SYM.cif')
#structure.to(filename='./here2-p1.cif')

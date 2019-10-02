#!/usr/bin/env python
import sys

from pymatgen import Structure
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.io.cif import CifWriter

filename = sys.argv[1]
filename_half = filename.split('.')[0]
structure = Structure.from_file(filename)
print(structure)
structure_p = SpacegroupAnalyzer(structure).find_primitive()
print(structure_p)
#sganalyzer = SpacegroupAnalyzer(structure)
cifwriter = CifWriter(structure, symprec=1.0e-4)
cifwriter.write_file(f'{filename_half}-SYM.cif')
cifwriter_p = CifWriter(structure_p, symprec=1.0e-4)
cifwriter_p.write_file(f'{filename_half}-SYM-p.cif')
cifwriter_p1 = CifWriter(structure_p)
cifwriter_p1.write_file(f'{filename_half}-SYM-p1.cif')
#structure.to(filename='./here2-p1.cif')

"""Regenerate S9 and its combined container from the existing full S7 release.

For full releases use build_standalone_supplements.py; this narrow path avoids
rewriting the lossless workbook during layout-only changes to S9.
"""
import csv
from openpyxl import load_workbook
import build_standalone_supplements as b
w=load_workbook(b.ROOT/'manuscript/bmc_supplementary_table_s7.xlsx',read_only=True,data_only=True)
h,*rows=list(w['STUDIES'].values);w.close()
with (b.OUT/'supplementary_manifest.tsv').open() as f:
    b.MANIFEST[:]=[r for r in list(csv.reader(f,delimiter='\t'))[1:] if r[0]!='Supplementary Table S9']
b.build_study_audit_table(b.INCLUDED,h,rows,b.emit_panelled_table)
b.build_manifest()
b.build_combined_publication_supplement()

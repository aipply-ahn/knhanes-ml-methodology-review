"""Targeted build: source view, Fig1 EN/KO, existing S3, combined supplement, mains."""
from pathlib import Path
import csv
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_openalex_source_view import build
import make_figures
import build_standalone_supplements as s

def main():
    build()
    from apply_kci_fulltext_rechecks import build as rechecks
    rechecks()
    # Refresh the module's flow loaded before the derived source view was built.
    s.FLOW=s.load_json('results/derived/final_selection_flow.json')
    make_figures.fig1_prisma();make_figures.fig1_prisma('ko')
    import make_streamlined_figures as f
    f.figure10_reproducibility();f.figure10_reproducibility('ko')
    with (ROOT/'manuscript/supplementary/supplementary_manifest.tsv').open() as f:
        old=list(csv.reader(f,delimiter='\t'))[1:]
    s.MANIFEST.clear();s.build_search_table_s3()
    s.MANIFEST[:]=[r for r in old if r[0]!='Supplementary Table S3']+s.MANIFEST
    s.build_manifest();s.build_combined_publication_supplement()
    subprocess.run(['make','en','ko'],cwd=ROOT/'manuscript',check=True)
if __name__=='__main__':main()

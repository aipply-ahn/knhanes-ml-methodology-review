"""Create and read back a self-contained revision snapshot without prior archives."""
from pathlib import Path
from datetime import datetime
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'prompts/implementation_records/cycle_080'
BASE=ROOT/'project_archive/submission_versions/v079_before_cycle_20260924_090253'

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def main():
 target=ROOT/json.loads((REC/'release_target.json').read_text())['directory']
 target.mkdir(parents=True,exist_ok=False)
 previous=json.loads((BASE/'manifest.json').read_text())
 files=set()
 # Include baseline-selected source/analysis inputs, not historical releases or credentials.
 for row in previous['files']:
  p=ROOT/row['path']
  if p.is_file() and row['path'].startswith(('manuscript/','tools/','data/','results/derived/')) and p.suffix not in ('.zip','.gz','.pyc'):
   files.add(p)
 for dirname in ['manuscript/supplementary','prompts/implementation_records/cycle_080']:
  files.update(p for p in (ROOT/dirname).rglob('*') if p.is_file() and p.suffix!='.pyc')
 files.update((ROOT/'tools').glob('*.py'))
 for pattern in ['*.tex','*.bib','*.cls','*.bst','*.sty']:
  files.update((ROOT/'manuscript').glob(pattern))
 files.update(ROOT/p for p in ['AGENTS.md','README.md','KNHANES_ML_study_audit_protocol.md','KNHANES_ML_study_audit_template_v1.2.json','manuscript/Makefile','manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf','manuscript/bmc_supplementary.pdf','manuscript/bmc_supplementary_table_s5.xlsx','manuscript/bmc_supplementary_table_s7.xlsx'])
 for row in json.loads((REC/'section_figure_message_source_map.json').read_text()):
  p=ROOT/row['active_file'];files.add(p)
  ko=p.with_name(p.stem+'_ko.pdf');files.add(ko)
  for q in [p,ko]:
   for ext in ['.pdf','.png']:
    figure=ROOT/'figures/submission'/q.with_suffix(ext).name
    if figure.exists():files.add(figure)
 # Source PDFs are immutable dependencies referenced through the verified baseline,
 # except official appraisal instruments, which are included for immediate inspection.
 for p in (ROOT/'references/guidelines').glob('PROBAST_AI*2025.pdf'):files.add(p)
 (REC/'baseline_dependency_reference.json').write_text(json.dumps({'baseline_directory':str(BASE.relative_to(ROOT)),'manifest_sha256':digest(BASE/'manifest.json'),'snapshot_sha256':digest(BASE/'snapshot.tar.gz'),'scope':'Unchanged source reports, original evidence excerpts, raw search caches and remaining input files not embedded here are referenced by the baseline per-file manifest. No source ambiguity is resolved by packaging.'},indent=2)+'\n')
 files.add(REC/'baseline_dependency_reference.json')
 files=sorted(files)
 manifest={'version':'v080','created_at':datetime.now().astimezone().isoformat(),'archive':'snapshot.tar.gz','baseline':str(BASE.relative_to(ROOT)),'files':[]}
 basehash={x['path']:x['sha256'] for x in previous['files']}
 for p in files:
  relative=str(p.relative_to(ROOT));h=digest(p)
  manifest['files'].append({'path':relative,'bytes':p.stat().st_size,'sha256':h,'baseline_relation':'unchanged' if basehash.get(relative)==h else 'modified' if relative in basehash else 'added'})
 (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 with tarfile.open(target/'snapshot.tar.gz','w:gz',compresslevel=6,dereference=True) as t:
  for p in files:t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
 expected={r['path']:r['sha256'] for r in manifest['files']};seen=set()
 with tarfile.open(target/'snapshot.tar.gz','r|gz') as t:
  for member in t:
   assert member.isfile(),member.name
   f=t.extractfile(member);h=hashlib.sha256()
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
   assert h.hexdigest()==expected[member.name],member.name
   seen.add(member.name)
 assert seen==set(expected)
 receipt={'status':'PASS','files_verified':len(seen),'archive_sha256':digest(target/'snapshot.tar.gz'),'manifest_sha256':digest(target/'manifest.json'),'readback':'Every archived file was decompressed and SHA-256 compared against manifest.json.'}
 (target/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (REC/'archive_receipt.json').write_text(json.dumps({'directory':str(target.relative_to(ROOT)),**receipt},indent=2)+'\n')
 print(str(target.relative_to(ROOT)),len(seen),'files: SHA-256 readback PASS',flush=True)
if __name__=='__main__':main()

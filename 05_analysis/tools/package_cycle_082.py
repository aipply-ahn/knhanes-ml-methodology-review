"""Snapshot v082 and verify every archived byte; external dependencies are separate."""
from pathlib import Path
from datetime import datetime
import json,hashlib,tarfile
ROOT=Path(__file__).resolve().parents[1];REC=ROOT/'prompts/implementation_records/cycle_082'
BASE=ROOT/'project_archive/submission_versions/v079_before_cycle_20260924_090253'
PREV=ROOT/'project_archive/submission_versions/v081_20260924_102044'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def row(p):return {'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)}
def main():
 target=ROOT/'project_archive/submission_versions'/datetime.now().strftime('v082_%Y%m%d_%H%M%S')
 target.mkdir(exist_ok=False)
 (REC/'release_target.json').write_text(json.dumps({'directory':str(target.relative_to(ROOT))},indent=2)+'\n')
 previous=json.loads((PREV/'manifest.json').read_text());files=set()
 for r in previous['files']:
  p=ROOT/r['path']
  if p.is_file() and r['path'].startswith(('manuscript/','tools/','data/','results/derived/')) and p.suffix not in ('.zip','.gz','.pyc'):files.add(p)
 for dirname in ['manuscript','tools','figures/submission','data/study_json','data/repository_release','data/protocol_v1_2/final','data/protocol_v1_3','results/derived','prompts/implementation_records/cycle_082','prompts/implementation_records/hermes_cycle_review']:
  files.update(p for p in (ROOT/dirname).rglob('*') if p.is_file() and p.suffix not in ('.pyc','.zip','.gz') and '__pycache__' not in p.parts)
 for path in ['prompts/implementation_records/cycle_080/protocol_before_ko.md',
              'project_archive/submission_versions/v079_before_cycle_20260924_090253/manifest.json',
              'project_archive/submission_versions/v080_20260924_093602/manifest.json',
              'project_archive/submission_versions/v081_20260924_102044/manifest.json',
              'prompts/implementation_records/cycle_081/README.md','prompts/implementation_records/cycle_081/rendered/figure_inventory.json','prompts/implementation_records/cycle_081/rendered/page_index.json','AGENTS.md','README.md','KNHANES_ML_study_audit_protocol.md','KNHANES_ML_study_audit_template_v1.2.json',
              'results/raw/openalex_20260905.json','results/raw/epmc_20260903.json','results/raw/pubmed_20260903.json','results/raw/kci_20260905/census.json',
              'project_archive/paper_cleanup_20260918_002038/internal/supplement_sources/appendix1_prisma_checklist.md']:
  p=ROOT/path;assert p.is_file(),path;files.add(p)
 files.update(p for p in (ROOT/'build/submission').glob('*.log') if p.is_file())
 files.update(p for p in (ROOT/'references/guidelines').rglob('*') if p.is_file())
 # Correct v080's unsupported baseline assertion. Actual dependencies are hashed now,
 # never claimed to have been embedded in an earlier manifest.
 external=[]
 for folder in ['references','results/raw']:
  for p in sorted((ROOT/folder).rglob('*')):
   if p.is_file() and p not in files:external.append(row(p))
 dependencies={'version':'v082','baseline_correction':'The v079 per-file manifest does not include references/pdf or results/raw. The v080 baseline_dependency_reference scope claim was overbroad and is not evidence of their archival inclusion. Older snapshots are unchanged.',
  'embedded_inputs':'See snapshot manifest for final protocol records, study_json topic inputs, derived inputs, required raw search-cache files and official guidelines.',
  'external_unembedded_dependencies':external,
  'scope':'External source files are identified by actual path, byte count and current SHA-256. They are not embedded in this snapshot; checksums permit identity verification if separately supplied. No source uncertainty is resolved by packaging.',
  'baseline_identity':row(BASE/'manifest.json'),'previous_identity':row(PREV/'manifest.json')}
 dep=REC/'dependency_record.json';dep.write_text(json.dumps(dependencies,ensure_ascii=False,indent=2)+'\n');files.add(dep)
 old={r['path']:r['sha256'] for r in json.loads((PREV/'manifest.json').read_text())['files']}
 changed=[row(p) for p in sorted(files) if str(p.relative_to(ROOT)).startswith(('tools/','manuscript/','KNHANES')) and old.get(str(p.relative_to(ROOT)))!=digest(p)]
 changedfile=REC/'changed_sources_and_outputs.json';changedfile.write_text(json.dumps(changed,indent=2)+'\n');files.add(changedfile)
 manifest={'version':'v082','created_at':datetime.now().astimezone().isoformat(),'archive':'snapshot.tar.gz','files':[row(p) for p in sorted(files)]}
 (target/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 # Inputs are frozen from this point through archive readback.
 with tarfile.open(target/'snapshot.tar.gz','w:gz',compresslevel=6,dereference=True) as t:
  for p in sorted(files):t.add(p,arcname=str(p.relative_to(ROOT)),recursive=False)
 expected={r['path']:r['sha256'] for r in manifest['files']};seen=set()
 with tarfile.open(target/'snapshot.tar.gz','r|gz') as t:
  for member in t:
   assert member.isfile(),member.name
   h=hashlib.sha256();f=t.extractfile(member)
   for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
   assert h.hexdigest()==expected[member.name],member.name
   seen.add(member.name)
 assert seen==set(expected)
 receipt={'status':'PASS','files_verified':len(seen),'archive_sha256':digest(target/'snapshot.tar.gz'),'manifest_sha256':digest(target/'manifest.json'),'external_dependencies_hashed':len(external),'readback':'All archived files decompressed and SHA-256 matched against manifest.'}
 (target/'verification.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (REC/'archive_receipt.json').write_text(json.dumps({'directory':str(target.relative_to(ROOT)),**receipt},indent=2)+'\n')
 print(target.relative_to(ROOT),len(seen),'files: readback PASS',flush=True)
if __name__=='__main__':main()

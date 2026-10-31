"""Verify old archive bytes and decompress the verified immediate baseline."""
from pathlib import Path
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/cycle_083'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
rows=json.loads((OUT/'previous_archive_hashes.json').read_text())
for r in rows:assert sha(ROOT/r['path'])==r['sha256'],r['path']
checks={}
for folder in (ROOT/'project_archive/submission_versions').glob('v*'):
 p=folder/'verification.json'
 if not p.exists():continue
 r=json.loads(p.read_text())
 if r.get('status')!='PASS':continue
 for name,key in [('snapshot.tar.gz','archive_sha256'),('manifest.json','manifest_sha256')]:
  if key in r:
   assert sha(folder/name)==r[key],str(folder/name)
   checks[str((folder/name).relative_to(ROOT))]='Matches pre-existing verification receipt'
base=ROOT/'project_archive/submission_versions/v082_20260924_104700'
expected={r['path']:r['sha256'] for r in json.loads((base/'manifest.json').read_text())['files']};seen=set()
with tarfile.open(base/'snapshot.tar.gz','r|gz') as t:
 for m in t:
  h=hashlib.sha256();f=t.extractfile(m)
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
  assert h.hexdigest()==expected[m.name],m.name
  seen.add(m.name)
assert seen==set(expected)
report={'status':'PASS','all_previous_archive_files_unchanged':len(rows),'preexisting_receipts':checks,'immediate_baseline_decompressed_hash_verified':len(seen),'preserved_failed_candidate':'v081_20260924_101923 remains unchanged and is not reclassified as a release'}
(OUT/'prior_versions_unchanged.json').write_text(json.dumps(report,indent=2)+'\n');print(report)

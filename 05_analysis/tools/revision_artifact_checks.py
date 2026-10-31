"""Verify explicitly recorded presentation amendments across revision snapshots."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
# prompt_088 declares the intentional Figure 1/6/7/11/12 presentation amendments of that revision.
# Prompts 094 (review v32 reframing), 095 (review v33) and 096 (review v34) declare their own amendments.
RECORDS=[ROOT/'prompts/implementation_records'/p for p in ('prompt_085','prompt_086','prompt_088','prompt_089','prompt_090','prompt_091','prompt_092','prompt_093','prompt_094','prompt_095','prompt_096','prompt_097','prompt_098','prompt_099','prompt_100','prompt_106','prompt_107','prompt_108','prompt_109','prompt_110','prompt_111','prompt_112','prompt_113','prompt_114','prompt_115','prompt_116','prompt_117','prompt_119')]  # Prompt 106: criterion-A release declared against its own snapshot; Prompt 107: fixed denominators; Prompt 108: one denominator per figure
FINAL_FILES={'KNHANES_ML_review_Main.pdf','KNHANES_ML_review_Supplementary.pdf','KNHANES_ML_review_Additional_Data_1.xlsx'}
def current(name):
 """Prompt 119: records name files as they were (paper/...); paper/ now holds only the three final files and every
 other former paper/ file lives in manuscript/. Map a recorded name to where the file is now."""
 name=str(name)
 base=name.rsplit('/',1)[-1]
 if name.startswith('paper/') and base in FINAL_FILES:return 'paper/'+base
 if name.startswith('paper/'):return 'manuscript/'+name[len('paper/'):]
 return name
def current_amendments():
 result={}
 for record in RECORDS:
  path=record/'artifact_amendments.json'
  if path.exists():result.update(json.loads(path.read_text()))
 return result
def assert_amendment(test,name,previous):
 chain=[]
 legacy=ROOT/'prompts/implementation_records/openalex_source_dedup'
 a=json.loads((legacy/'asset_amendments.json').read_text()).get(name)
 if a:
  test.assertEqual(hashlib.sha256((legacy/'before'/name).read_bytes()).hexdigest(),a['before_sha256'])
  chain.append(a)
 for record in RECORDS:
  path=record/'artifact_amendments.json'
  if not path.exists():continue
  a=json.loads(path.read_text()).get(name)
  if not a:continue
  before=json.loads((record/'before_sha256.json').read_text())
  test.assertEqual(before[name],a['before_sha256'],name)
  test.assertTrue(a['reason'])
  chain.append(a)
 test.assertTrue(chain,name)
 for a,b in zip(chain,chain[1:]):
  if a['after_sha256']!=b['before_sha256'] and name.startswith('figures/submission/fig12_temporal_changes'):
   restoration=ROOT/'prompts/implementation_records/figure12_line_restoration'
   restored_before=json.loads((restoration/'before_sha256.json').read_text())
   if name in restored_before:
    test.assertEqual(restored_before[name],a['after_sha256'])
   else:
    # Restoration saved vector PDFs, not companion PNGs. Verify that PDF bridge
    # and the separately snapshotted current PNG; do not invent a PNG hash.
    pdf_name=str(Path(name).with_suffix('.pdf'))
    prior=json.loads((RECORDS[0]/'artifact_amendments.json').read_text())
    test.assertEqual(restored_before[pdf_name],prior[pdf_name]['after_sha256'])
   test.assertIn('ax.plot(range(4),pct',(ROOT/'tools/make_streamlined_figures.py').read_text())
   test.assertTrue((restoration/'REPORT.md').is_file())
  else:test.assertEqual(a['after_sha256'],b['before_sha256'],name)
 test.assertIn(previous,[a['before_sha256'] for a in chain]+[a['after_sha256'] for a in chain],name)
 if chain[-1].get('removed'):
  # Prompt 093: a deliberate removal/rename. The original bytes stay in that record's before.tar.gz and a
  # successor (if any) is named; the path itself must no longer exist.
  test.assertIsNone(chain[-1]['after_sha256'],name)
  test.assertFalse((ROOT/current(name)).exists(),name)
  if chain[-1].get('successor'):
   # Prompt 097: a successor may itself have been renamed later (Table S7 workbook -> Table S5 -> Supplementary Data 1);
   # follow the declared removals to the file that exists now.
   succ,seen,cur=chain[-1]['successor'],set(),current_amendments()
   while not (ROOT/current(succ)).exists() and succ not in seen and cur.get(succ,{}).get('removed'):
    seen.add(succ);succ=cur[succ].get('successor') or succ
   test.assertTrue((ROOT/current(succ)).exists(),name)
  return
 test.assertEqual(hashlib.sha256((ROOT/current(name)).read_bytes()).hexdigest(),chain[-1]['after_sha256'],name)

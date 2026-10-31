"""Current revision invariants and final-page render inventory; never edits archives."""
from pathlib import Path
import csv,hashlib,json,tarfile,io,zipfile,subprocess,sys,tempfile
import fitz
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prompts/implementation_records/prompt_085'
import os
RECORD=Path(os.environ.get('KNHANES_VERIFY085_RECORD',ROOT/'prompts/implementation_records/prompt_086/prompt085_verification'))
RECORD.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 checks={}
 before=json.loads((OUT/'before_sha256.json').read_text())
 with tarfile.open(OUT/'before.tar.gz') as t:
  protected=json.loads((OUT/'protected_sha256.json').read_text())
  # Prompt archival legitimately appends exactly one manifest row after all
  # deliverables pass. Verify that append explicitly; every other protected
  # file must retain its frozen hash.
  manifest='prompts/processed/manifest.tsv'
  a106=json.loads((ROOT/'prompts/implementation_records/prompt_106/artifact_amendments.json').read_text())
  assert all(p==manifest or sha(ROOT/p)==h or (p in a106 and sha(ROOT/p)==a106[p]['after_sha256']) for p,h in protected.items())  # Prompt 106
  receipt=json.loads((OUT/'archive_verification.json').read_text())
  with (ROOT/manifest).open(newline='',encoding='utf-8') as f:
   rows=list(csv.DictReader(f,delimiter='\t'))
  # Later prompts append further rows; verify the prompt-085 row itself rather than the last row.
  row85=[r for r in rows if r['prompt_no']=='85'];assert len(row85)==1
  assert row85[0]['archived_path']=='prompts/processed/prompt_085_20260925_095337.txt'
  assert len({r['prompt_no'] for r in rows})==len(rows)
  for row in rows:
   archived=ROOT/row['archived_path']
   assert archived.is_file() and sha(archived)==row['sha256'],row['archived_path']
  assert receipt['manifest_only_appended_one_row'] and receipt['expected_prompt_number']==85
  checks['protected_raw_sources_final_responses_and_latest_records']=len(protected)
  checks['processed_prompt_manifest']='all archived prompt hashes verified; prompt 085 is final row'
  for p,h in before.items():assert hashlib.sha256(t.extractfile(p).read()).hexdigest()==h,p
  checks['verified_snapshot_files']=len(before)
  for name in ('manuscript/bmc_main.tex','manuscript/bmc_main_ko.tex'):
   old=t.extractfile(name.replace('manuscript/','paper/',1)).read().decode();new=(ROOT/name).read_text()
   assert old.split('\\begin{document}')[0]==new.split('\\begin{document}')[0]
  for name in ['manuscript/sn-jnl.cls','manuscript/protocol_v1_2_numbers.tex','results/derived/figure11_reporting_probast_domain_audit.json']:k=name.replace('manuscript/','paper/',1);assert sha(ROOT/name)==before[k] or (k in a106 and a106[k]['before_sha256']==before[k] and sha(ROOT/name)==a106[k]['after_sha256']),name  # Prompt 106
  checks['preambles_class_constants_figure11_data']='unchanged; figure typography intentionally amended by prompt086'
  old=load_workbook(io.BytesIO(t.extractfile('paper/bmc_supplementary_table_s7.xlsx').read()),read_only=True,data_only=True)
  # Prompt 093: the study-level workbook is Supplementary Table S5 (renamed file, same sheets plus reader sheets).
  new=load_workbook(ROOT/'manuscript/bmc_supplementary_data1.xlsx',read_only=True,data_only=True)  # Prompt 097: Additional Data 1
  for sheet in old.sheetnames:
   # Prompt 092 renumbered the supplement, so the README sheet's S2/S9 references changed intentionally.
   if sheet=='README':continue
   ov,nv=list(old[sheet].values),list(new[sheet].values)
   if ov!=nv:  # Prompt 106: criterion A drops KHM073/129/156 and adds new studies; every other original row must survive
    import re as _re
    norm=lambda r:tuple(_re.sub(r'[A-Z_]+![A-Z]+\d+','<CELL>',x).replace('250 included studies','220 included studies').replace('(n=238)','(n=208)') if isinstance(x,str) else x for x in r)
    assert ov[0]==nv[0],sheet
    keep=set(map(norm,nv[1:]))
    assert all(norm(r) in keep for r in ov[1:] if not (r and r[0] in {'KHM073','KHM129','KHM156'})),sheet
  assert set(new.sheetnames)-set(old.sheetnames)=={'PURPOSE_OUTPUT_2X2','PURPOSE_OUTPUT_STUDIES','VARIABLE_DICTIONARY','ML_ADJACENT_REPORTS','PROTOCOL_ITEMS','PROTOCOL_RESPONSE_CODES','ASSESSMENT_SCOPE','ASSESSMENT_VALIDATION_SURVEY','ASSESSMENT_APPRAISAL','ASSESSMENT_RECOVERY_VS_REPORTING','ASSESSMENT_SOURCE_RECHECKS','VARIABLE_HARMONISATION','RANKING_VARIABLES','SENSITIVITY_ANALYSES'}  # Prompt 112: Figure 5 harmonisation sheets  # prompt 113: sensitivity sheet
  checks['original_s7_sheets_cell_identical']=len(old.sheetnames);checks['current_s7_sheets']=len(new.sheetnames)
  old.close();new.close()
  render=RECORD/'rendered';render.mkdir(exist_ok=True);index=[];page_counts={}
  # Render every visually changed final page at 96 dpi, without enlarging the text block.
  # Prompt 092: manuscript/bmc_main*.pdf also carry the landscape supplement pages, so page geometry is
  # compared on the manuscript-only builds (the locked BMC page size applies to the manuscript).
  for name in ['manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf','manuscript/bmc_supplementary.pdf']:
   current=ROOT/name if name.endswith('supplementary.pdf') else ROOT/'build/submission'/Path(name).name
   a=fitz.open(stream=t.extractfile(name.replace('manuscript/','paper/',1)).read(),filetype='pdf');b=fitz.open(current)
   page_counts[name]={'before':len(a),'after':len(b)}
   for i,p in enumerate(b):
    # Prompt 095 (review v33): supplement Figure S6 is a portrait 2x3 grid, so its page is the portrait A4 of the manuscript.
    # Prompt 096 (review v34): Figure S5 is also portrait; Table S9 is a new last page (landscape like the other tables).
    head=p.get_text()[:200]
    # Prompt 097 (review v35): every supplementary figure page is portrait A4; table pages stay landscape.
    if name.endswith('bmc_supplementary.pdf') and 'Supplementary Figure S' in head:
     assert round(p.rect.width)==595 and round(p.rect.height)==842,(name,i)
    elif name.endswith('bmc_supplementary.pdf') and head.startswith('Supplementary contents'):
     assert p.rect.width>0,(name,i)  # Prompt 097: the contents page keeps the combined-document page, whatever its first item
    elif name.endswith('bmc_supplementary.pdf') and 'Supplementary Table S' in head:
     assert p.rect.width>p.rect.height,(name,i)
    else:
     assert p.rect==a[min(i,len(a)-1)].rect,(name,i)
    pix=p.get_pixmap(matrix=fitz.Matrix(96/72,96/72))
    oldpix=a[i].get_pixmap(matrix=fitz.Matrix(96/72,96/72)) if i<len(a) else None
    if oldpix and hashlib.sha256(pix.samples).digest()==hashlib.sha256(oldpix.samples).digest():continue
    dest=render/f'{Path(name).stem}_p{i+1:03}.png';pix.save(dest)
    index.append(dict(pdf=name,page=i+1,width_pt=p.rect.width,height_pt=p.rect.height,render=str(dest.relative_to(ROOT))))
   if name.endswith('bmc_supplementary.pdf'):
    assert len(b.get_toc())==16;checks['supplement_bookmarks']=16  # Prompt 099: Tables S1-S8 + Figures S1-S8 (former Figure 4C is S7)
   a.close();b.close()
  (render/'index.json').write_text(json.dumps(index,indent=2)+'\n')
  checks['page_counts']=page_counts;checks['changed_final_pages']=len(index)
 with tempfile.TemporaryDirectory() as tmp:
  with zipfile.ZipFile(ROOT/'manuscript/reviewer_delivery.zip') as z:z.extractall(tmp)
  r=subprocess.run([sys.executable,str(Path(tmp)/'verify_delivery.py')],capture_output=True,text=True)
  (RECORD/'extracted_zip_verification.log').write_text(r.stdout+r.stderr);assert r.returncode==0,r.stderr
  checks['extracted_delivery']=json.loads(r.stdout)
 changed={p:{'before':h,'after':sha(ROOT/p) if (ROOT/p).is_file() else None} for p,h in before.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h}
 (RECORD/'changed_files.json').write_text(json.dumps(changed,indent=2)+'\n')
 checks['changed_snapshot_paths']=len(changed)
 (RECORD/'verification.json').write_text(json.dumps(checks,indent=2)+'\n');print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)

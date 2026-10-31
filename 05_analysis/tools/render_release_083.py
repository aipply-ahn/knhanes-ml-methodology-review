"""Render final changed pages and inventory unchanged figure assets."""
from pathlib import Path
import hashlib,json,re,tarfile
import fitz
ROOT=Path(__file__).resolve().parents[1];REC=ROOT/'prompts/implementation_records/cycle_083'
OUT=REC/'rendered';OUT.mkdir(exist_ok=True)
previous=ROOT/'project_archive/submission_versions/v082_20260924_104700'
manifest={r['path']:r['sha256'] for r in json.loads((previous/'manifest.json').read_text())['files']}
figs=[]
for p in sorted((ROOT/'figures/submission').rglob('*')):
 if p.is_file() and str(p.relative_to(ROOT)) in manifest:
  same=hashlib.sha256(p.read_bytes()).hexdigest()==manifest[str(p.relative_to(ROOT))]
  figs.append({'path':str(p.relative_to(ROOT)),'byte_identical':same})
  assert same or p.name.startswith(('fig7_predictor_training','fig9_validation_evaluation'))
index={}
for name in ['bmc_main','bmc_main_ko']:
 doc=fitz.open(ROOT/f'manuscript/{name}.pdf');selected=set();keys={}
 for i,page in enumerate(doc):
  text=page.get_text()
  if any(t in text for t in ['Reporting in at least one','보고 상태 (N=165)','Missing-data strategies','결측자료 처리방법 (N=165)']):selected.add(i+1)
  if any(t in text for t in ['positive integer','양의 정수','108/165','37/165']):selected.add(i+1)
 for number in sorted(selected):doc[number-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/f'{name}_{number:03}.png')
 index[name]={'pages':len(doc),'rendered':sorted(selected)}
for num in ['02','05','09']:
 p=next((ROOT/'manuscript/supplementary/pdf').glob('Supplementary_Table_S'+num+'_*.pdf'));doc=fitz.open(p)
 if num=='05':
  selected={i+1 for i,page in enumerate(doc) if any(t in re.sub(r'\s+','',page.get_text()) for t in ['H_threshold_reported','H_evaluation_sample_size','H_threshold_selection_method','H_evaluation_prevalence_identifiable'])}
 else:selected={1,2} if num=='02' else {1,len(doc)}
 for number in sorted(selected):doc[number-1].get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(OUT/f'S{num}_{number:03}.png')
 index['S'+num]={'pages':len(doc),'rendered':sorted(selected)}
with tarfile.open(previous/'snapshot.tar.gz') as archive:
 p='manuscript/supplementary/pdf/Supplementary_Table_S09_Study_protocol_audit_results.pdf'
 a=fitz.open(stream=archive.extractfile(p).read(),filetype='pdf');b=fitz.open(ROOT/p)
 identical=len(a)==len(b) and all(x.get_pixmap(matrix=fitz.Matrix(1,1)).samples==y.get_pixmap(matrix=fitz.Matrix(1,1)).samples for x,y in zip(a,b))
 index['S09']['all_pages_raster_identical_v082']=identical
 # Full prior-page visual preservation check for unchanged figure assets is above.
(REC/'figure_preservation.json').write_text(json.dumps(figs,indent=2)+'\n')
(OUT/'page_index.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps(index,indent=2))

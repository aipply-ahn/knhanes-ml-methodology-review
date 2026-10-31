"""Final bounded regression run and fresh PDF renders for this reporting revision."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,zipfile
import fitz
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prompts/implementation_records/openalex_source_dedup'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 tests=['tools/test_openalex_source_preprocessing.py','tools/test_prisma_publication_hierarchy.py','tools/test_prisma_reader_revision.py','tools/validate_figure11_spacing.py','prompts/implementation_records/prompt_reassessment/test_corrections.py','prompts/implementation_records/prompt_reassessment/test_delivery.py']
 results=[]
 for p in tests:
  r=subprocess.run([sys.executable,p],cwd=ROOT,text=True,capture_output=True)
  (OUT/(Path(p).stem+'.log')).write_text(r.stdout+r.stderr)
  results.append(dict(test=p,exit_code=r.returncode));assert r.returncode==0,p
 with tempfile.TemporaryDirectory() as temp:
  with zipfile.ZipFile(ROOT/'manuscript/reviewer_delivery.zip') as z:z.extractall(temp)
  r=subprocess.run([sys.executable,str(Path(temp)/'verify_delivery.py')],text=True,capture_output=True)
  (OUT/'extracted_zip_verification.log').write_text(r.stdout+r.stderr);assert r.returncode==0
 out=OUT/'rendered';out.mkdir(exist_ok=True);renders=[]
 for path in ['manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf','manuscript/bmc_supplementary.pdf','manuscript/supplementary/pdf/Supplementary_Table_S03_Search_strategies_and_yields.pdf','figures/submission/fig1_prisma.pdf','figures/submission/fig1_prisma_ko.pdf','figures/submission/fig11_methodological_appraisal.pdf','figures/submission/fig11_methodological_appraisal_ko.pdf']:
  with fitz.open(ROOT/path) as d:
   for i,p in enumerate(d):
    t=p.get_text()
    if not ('9,998' in t or 'W4225324040' in t or '236/259' in t or len(d)==1):continue
    dest=out/f'{Path(path).stem}_p{i+1}.png';p.get_pixmap(matrix=fitz.Matrix(1.6,1.6)).save(dest)
    renders.append(dict(pdf=path,page=i+1,render=str(dest.relative_to(ROOT))))
    if '236/259' in t:
     for label,frac in [('A',(0,.05,1,.46)),('CD',(0,.30,1,.82))]:
      r=p.rect;clip=fitz.Rect(frac[0]*r.width,frac[1]*r.height,frac[2]*r.width,frac[3]*r.height)
      p.get_pixmap(matrix=fitz.Matrix(2.5,2.5),clip=clip).save(out/f'{Path(path).stem}_p{i+1}_{label}.png')
 for p in ['manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf']:
  with fitz.open(ROOT/p) as a,fitz.open(OUT/'before'/p) as b:
   assert all(page.rect==b[0].rect for page in a)
 # Ratios are category counts over actual appraisal units, not 165 studies.
 audit=json.loads((ROOT/'results/derived/figure11_reporting_probast_domain_audit.json').read_text())
 pd=audit['probast_ai']['development'];pe=audit['probast_ai']['evaluation']
 assert sum(pd['rows']['Overall'].values())==pd['unit_n']==259
 assert sum(pe['rows']['Overall'].values())==pe['unit_n']==346
 files=['manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf','manuscript/bmc_supplementary.pdf','manuscript/reviewer_delivery.zip','results/derived/openalex_source_input_view.json','results/derived/openalex_source_preprocessing.json','results/derived/final_selection_flow.json']
 result=dict(tests=results,extracted_zip_verifier='PASS',page_geometry_unchanged=True,figure11_unit_totals=[pd['unit_n'],pe['unit_n']],counts=json.loads((ROOT/'results/derived/openalex_source_preprocessing.json').read_text())['counts'],renders=renders,sha256={p:sha(ROOT/p) for p in files})
 (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n');(out/'index.json').write_text(json.dumps(renders,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()

"""Run release checks, record actual artifacts, and create a new review bundle."""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
import fitz
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prompts/implementation_records/prompt_079'

def main():
    logs={}
    for name in ['validate_prompt_079.py','validate_human_protocol_publication.py',
                 'validate_protocol_manuscript_propagation.py','KNHANES_preverification_alignment_validator.py',
                 'validate_korean_manuscript.py','validate_figure11_spacing.py']:
        r=subprocess.run([sys.executable,str(ROOT/'tools'/name)],cwd=ROOT,text=True,capture_output=True)
        (OUT/(name+'.log')).write_text(r.stdout+r.stderr)
        logs[name]=r.returncode
        print(name,r.returncode,flush=True)
        assert r.returncode==0,name
    # Do not overwrite earlier prompt implementation records.
    import validate_prompt_077 as regression
    regression.OUT=OUT/'regression_077'
    regression.main()
    import audit_protocol_publication_content as content
    content.OUT=OUT/'content_audit'
    content.main()
    checks={}
    checks['source_response_verification_pass']=json.loads((OUT/'verification.json').read_text())['status']=='PASS'
    w=load_workbook(ROOT/'manuscript/bmc_supplementary_table_s7.xlsx',read_only=True,data_only=True)
    checks['s7_copy_identical']=(ROOT/'manuscript/bmc_supplementary_table_s7.xlsx').read_bytes()==(ROOT/'manuscript/supplementary/tables/Supplementary_Table_S07_Master_study_level_dataset.xlsx').read_bytes()
    checks['24_relational_sheets']=len(w.sheetnames)==24
    header,*sr=list(w['STUDIES'].values)
    studies={r[0]:dict(zip(header,r)) for r in sr}
    s6=load_workbook(ROOT/'manuscript/supplementary/tables/Supplementary_Table_S06_Noncore_health_analysis_studies.xlsx',read_only=True,data_only=True)
    rows=list(s6.active.values)
    checks['s6_english_descriptions']=not any(re.search('[가-힣]',str(v or '')) for r in rows for v in r)
    checks['s6_na_not_absence']=all(any(sid in str(r[0]) and 'prediction-model code item not applicable' in str(r[-1]) for r in rows)
                                  for sid in ('KHM012','KHM031','KHM038','KHM059','KHM156','KHM179'))
    checks['s6_does_not_add_khm151']=not any('KHM151' in str(r) for r in rows)
    checks['source_na_unchanged']=all(studies[s]['K_code_available']=='NA' for s in ('KHM012','KHM031','KHM038','KHM059','KHM151','KHM156','KHM179'))
    s6.close();w.close()
    locked=[]
    for p in (ROOT/'data/protocol_v1_2/final').glob('*_final.json'):
        d=json.loads(p.read_text())
        locked.append(hashlib.sha256(json.dumps(d['protocol_items'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()==d['protocol_items_sha256'])
    checks['all_222_locked_response_hashes_unchanged']=len(locked)==222 and all(locked)
    with (ROOT/'data/protocol_v1_2/KNHANES_studies_v1.2.jsonl').open() as f:
        count=0
        for line in f:
            d=json.loads(line);count+=1
            assert d==json.loads((ROOT/f"data/protocol_v1_2/final/{d['study_id']}_final.json").read_text())
    checks['merged_222_records_equal_final']=count==222
    checks['no_supplement_box_overflow']=not re.search(r'Overfull \\[hv]box',(ROOT/'build/submission/bmc_supplementary.log').read_text())
    bounds=[];pages={}
    for p in sorted((ROOT/'manuscript/supplementary/pdf').glob('*.pdf')):
        doc=fitz.open(p);pages[p.name]=len(doc)
        for i,page in enumerate(doc):
            for block in page.get_text('dict')['blocks']:
                for line in block.get('lines',[]):
                    for span in line['spans']:
                        x0,y0,x1,y1=span['bbox']
                        if x0 < -1 or y0 < -1 or x1>page.rect.width+1 or y1>page.rect.height+1:
                            bounds.append([p.name,i+1,span['text']])
    checks['all_supplement_text_within_pages']=not bounds
    report={'status':'PASS' if all(checks.values()) else 'FAIL','commands':logs,'checks':checks,
            'pdf_pages':pages,'out_of_page_spans':bounds}
    (OUT/'final_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    assert all(checks.values()),report
    print('FINAL CHECKS PASS',flush=True)
    if '--package' not in sys.argv:return
    files=[ROOT/p for p in ['KNHANES_ML_study_audit_protocol.md','manuscript/bmc_main.tex','manuscript/bmc_main_ko.tex',
         'manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf','manuscript/bmc_supplementary.tex','manuscript/bmc_supplementary.pdf',
         'references/guidelines/PROBAST_AI_official_tool_2025.pdf','references/guidelines/PROBAST_AI_EE_Light_2025.pdf']]
    files+=list((ROOT/'manuscript/supplementary').rglob('*'))
    files+=list(OUT.rglob('*'))
    files+=list((ROOT/'prompts/processed').glob('prompt_079_*.txt'))
    files += [ROOT/'tools'/name for name in ['build_standalone_supplements.py','public_response_tables.py',
        'public_variable_definitions.py','analysis_content_supplements.py','protocol_record_schema.py',
        'apply_prompt_079_content.py','protocol_public_english.py','complete_protocol_evidence.py',
        'validate_prompt_079.py','validate_human_protocol_publication.py','validate_protocol_manuscript_propagation.py',
        'KNHANES_preverification_alignment_validator.py','check_and_package_prompt_079.py']]
    files=sorted({p for p in files if p.is_file()})
    target=ROOT/'manuscript/protocol_publication_revision_079.zip'
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for p in files:z.write(p,str(p.relative_to(ROOT)))
        z.writestr('SHA256SUMS.tsv','sha256\tfile\n'+''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'\t'+str(p.relative_to(ROOT))+'\n' for p in files))
    with ZipFile(target) as z:assert z.testzip() is None
    print('Packaged',target.relative_to(ROOT))
if __name__=='__main__':main()

#!/usr/bin/env python3
"""Bundle the verified prompt-077 revision without overwriting older packages."""
import csv
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from build_standalone_supplements import protocol_items
from protocol_public_english import english_item

ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT/'prompts/implementation_records/prompt_077'

def main():
    result = json.loads((NOTES/'verification.json').read_text())
    assert result['status'] == 'PASS'
    for name,digest in result['sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == digest, name
    with (NOTES/'translation_crosswalk.tsv').open('w',newline='') as f:
        w=csv.writer(f,delimiter='\t')
        w.writerow(['item_id','canonical_question','english_question','canonical_rule','english_rule'])
        for item in protocol_items():
            if item['item_role'] in {'reviewer_entered','appraisal_judgement'}:
                translated=english_item(item)
                w.writerow([item['item_id'],item['question'],translated['question'],item['decision_rule'],translated['decision_rule']])
    files=[ROOT/p for p in ('KNHANES_ML_study_audit_protocol.md','manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf',
        'manuscript/bmc_supplementary.pdf','tools/protocol_public_english.py','tools/protocol_record_schema.py',
        'tools/validate_prompt_077.py','tools/build_standalone_supplements.py','tools/make_streamlined_figures.py')]
    files += sorted((ROOT/'manuscript/supplementary/pdf').glob('*.pdf'))
    files += sorted((ROOT/'manuscript/supplementary/tables').glob('*.xlsx'))
    files += sorted(NOTES.glob('*'))
    files += sorted((ROOT/'prompts/processed').glob('prompt_077_*.txt'))
    files += [ROOT/'prompts/implementation_records/protocol_content_audit_20260924'/n
              for n in ('audit.json','item_comparison.tsv','source_content_gaps.tsv')]
    target=ROOT/'manuscript/protocol_publication_revision_077.zip'
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for p in files:
            if p.is_file(): z.write(p,str(p.relative_to(ROOT)))
        z.writestr('SHA256SUMS.tsv','sha256\tfile\n'+''.join(
            f'{hashlib.sha256(p.read_bytes()).hexdigest()}\t{p.relative_to(ROOT)}\n' for p in files if p.is_file()))
        z.writestr('README.txt','프롬프트 077 내부 검토용 완료본. 처리 내용은 prompts/implementation_records/prompt_077/README.md를 확인하십시오. 전체 정본의 공개 기탁을 뜻하지 않습니다.\n')
    with ZipFile(target) as z: assert z.testzip() is None
    print(target.relative_to(ROOT))

if __name__=='__main__': main()

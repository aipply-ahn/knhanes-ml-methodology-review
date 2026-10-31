"""Reproduce the complete English canonical protocol from archived Korean source.

Exact paragraph/cell mappings retain structural metadata and historical records.
"""
from pathlib import Path
import json,re
from protocol_public_english import QUESTIONS, PHRASES
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'prompts/implementation_records/cycle_080'
def main():
    source=(REC/'protocol_before_ko.md').read_text()
    lines=[]
    for line in source.splitlines():
        if re.match(r'^\|\s*\d+\s*\|\s*`',line):
            c=[v.strip() for v in line.strip('|').split('|')]
            iid=c[1].strip('`')
            if iid in QUESTIONS:c[8]=QUESTIONS[iid]
            c=[PHRASES.get(v,v) for v in c]
            line='| '+' | '.join(c)+' |'
        lines.append(line)
    source='\n'.join(lines)+'\n'
    units=json.loads((REC/'translation_source_units.json').read_text())
    mapping={int(k):v for k,v in json.loads((REC/'translation_cells.json').read_text()).items()}
    for n,t in re.findall(r'^@@(\d+)\n(.*?)(?=^@@\d+\n|\Z)',(REC/'translation_segments.txt').read_text(),re.M|re.S):
        assert int(n) not in mapping,n
        mapping[int(n)]=t.strip()
    assert set(mapping)==set(range(len(units))),set(range(len(units)))-set(mapping)
    for i in sorted(mapping,key=lambda i:len(units[i]),reverse=True):
        assert units[i] in source,(i,units[i])
        source=source.replace(units[i],mapping[i])
    assert not re.search('[가-힣]',source)
    (ROOT/'KNHANES_ML_study_audit_protocol.md').write_text(source)
    (REC/'translation_manifest.json').write_text(json.dumps({'translated_segments':len(mapping),'core_items':382,'source':'protocol_before_ko.md','mapping_files':['translation_cells.json','translation_segments.txt']},indent=2)+'\n')
if __name__=='__main__':main()

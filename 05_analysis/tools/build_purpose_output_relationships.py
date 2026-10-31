"""Study-level Fig3 intersections; no inferred analysis-level linkage."""
from pathlib import Path
import json,hashlib,csv
ROOT=Path(__file__).resolve().parents[1]
def build():
    paths=['results/derived/study_purpose_audit.json','data/protocol_v1_3/purpose_evidence_addendum.json']
    purpose=json.loads((ROOT/paths[0]).read_text())['records']
    add={r['study_id']:r for r in json.loads((ROOT/paths[1]).read_text())['records']}
    rows=[]
    for r in purpose:
        if r['study_category']!='HEALTH_ANALYSIS':continue
        rows.append(dict(study_id=r['study_id'],interpretation_purpose='VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION' in r['health_analysis_purpose_components'],importance_output='VARIABLE_CONTRIBUTION_OR_RANK' in r['analytic_outputs'],association_purpose='POPULATION_ASSOCIATION_ANALYSIS' in r['health_analysis_purpose_components'],association_output=add[r['study_id']]['association_audit']['any_association_estimate_reported']=='Y'))
    pairs=[]
    for name,p,o in [('Variable interpretation / importance','interpretation_purpose','importance_output'),('Population association / association estimate','association_purpose','association_output')]:
        cells={label:[r['study_id'] for r in rows if r[p]==a and r[o]==b] for label,a,b in [('both',True,True),('purpose_only',True,False),('output_only',False,True),('neither',False,False)]}
        pairs.append(dict(relationship=name,purpose_field=p,output_field=o,denominator=len(rows),counts={k:len(v) for k,v in cells.items()},study_ids=cells))
    result=dict(schema='purpose_output_relationships_v1',unit='Study-level co-reporting; not same-analysis linkage, temporal ordering, or evidence of unplanned analysis',source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},rows=rows,relationships=pairs)
    (ROOT/'results/derived/purpose_output_relationships.json').write_text(json.dumps(result,indent=2)+'\n')
    with (ROOT/'results/derived/purpose_output_relationships.tsv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
    return result
if __name__=='__main__':print(json.dumps(build()['relationships'],indent=2))

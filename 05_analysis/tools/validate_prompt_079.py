"""Full source-to-public comparison; no row-count-only completeness claim."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from openpyxl import load_workbook

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'prompts/implementation_records/prompt_079'

def human(v):
    if v is None:return '(null)'
    if isinstance(v,bool):return str(v).lower()
    if isinstance(v,list):return '\n'.join(map(human,v)) if v else '(empty list)'
    if isinstance(v,dict):return '\n'.join(k+': '+human(x) for k,x in v.items()) if v else '(empty object)'
    return str(v) if v!='' else '(empty string)'

def rows(wb,name):
    r=iter(wb[name].values);h=next(r)
    for v in r:yield dict(zip(h,v))

def main():
    OUT.mkdir(exist_ok=True)
    path=ROOT/'manuscript/bmc_supplementary_table_s7.xlsx'
    w=load_workbook(path,read_only=True,data_only=True)
    studies={r['A_study_id']:r for r in rows(w,'STUDIES')}
    docs={sid:json.loads((ROOT/f'data/protocol_v1_2/final/{sid}_final.json').read_text()) for sid in studies}
    assert len(docs)==220
    for sid,d in docs.items():
        assert hashlib.sha256(json.dumps(d['protocol_items'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()==d['protocol_items_sha256'],sid
    continuations=defaultdict(list)
    for r in rows(w,'TEXT_CONTINUATIONS'):
        continuations[r['cell_ref']].append((int(r['part_index']),r['text']))
    def restore(v):
        m=re.search(r'cell_ref=([^\]]+)\]',str(v or ''))
        return ''.join(t for _,t in sorted(continuations[m[1]])) if m else v
    # Complete technical backup, original scalar types and all properties.
    chunks=defaultdict(list);digests={};chunk_counts={}
    for r in rows(w,'SOURCE_JSON'):
        sid=r['study_id']; chunks[sid].append((int(r['chunk_index']),r['json_chunk']))
        digests[sid]=r['sha256_of_joined_json'];chunk_counts[sid]=int(r['chunk_count'])
    for sid, parts in chunks.items():
        assert len(parts)==chunk_counts[sid]
        assert [i for i,_ in sorted(parts)]==list(range(1,len(parts)+1))
        raw=''.join(t for _,t in sorted(parts))
        assert hashlib.sha256(raw.encode()).hexdigest()==digests[sid],sid
        assert json.loads(raw)==docs[sid],sid
    assert set(chunks)==set(docs)
    counts=Counter(); seen=set(); item_counts=defaultdict(Counter); unit_errors=[]; evidence_errors=[]
    registry={sid:{r['evidence_id'] for r in d['evidence_registry']} for sid,d in docs.items()}
    id_fields={'reports':'report_id','datasets':'dataset_id','outcomes':'outcome_id',
               'models':'model_id','developments':'development_id','evaluations':'evaluation_id'}
    known={sid:{r[id_fields[name]] for name,rlist in d['units'].items() if name in id_fields
                for r in rlist if r.get(id_fields[name])}|{sid} for sid,d in docs.items()}
    for sid,d in docs.items():
        for name,field in [('visual_objects','object_id'),('performance_metrics','metric_id'),('best_model_selections','selection_id')]:
            known[sid].update(r[field] for r in d.get(name,[]) if r.get(field))
    expected_count=sum(len(rs) for d in docs.values() for rs in d['protocol_items'].values())
    for public in rows(w,'ITEM_RESPONSES'):
        p={k:restore(v) for k,v in public.items()};sid=p['study_id'];item=p['item_id'];i=int(p['response_index'])-1
        original=docs[sid]['protocol_items'][item][i]
        key=(sid,item,p['primary_unit'],p['unit_id'],i)
        assert key not in seen,key
        seen.add(key);counts['responses']+=1
        for target, source in [('final_value','value'),('value_status','value_status'),('unit_id','unit_id'),
            ('primary_unit','primary_unit'),('related_ids','related_ids'),('evidence_ids','evidence_ids'),
            ('rationale','rationale'),('selected_source','review_stage'),('reviewer_id','reviewer_id'),
            ('response_status','status'),('json_key','json_key'),('item_role','item_role')]:
            assert p[target]==human(original.get(source)),(key,target)
        assert p['source_record_path']==f'protocol_items.{item}[{i}]'
        for eid in original.get('evidence_ids',[]):
            if eid not in registry[sid]:evidence_errors.append([sid,item,i+1,eid])
        if studies[sid]['B_core_health_classification']=='Y':
            item_counts[item][p['final_value']]+=1
        for related in original.get('related_ids',{}).values():
            for rid in related if isinstance(related,list) else [related]:
                if rid and rid not in known[sid]:unit_errors.append([sid,item,i+1,rid])
    assert len(seen)==expected_count
    selection_seen=set()
    for public in rows(w,'MODEL_SELECTIONS'):
        p={k:restore(v) for k,v in public.items()};sid=p['study_id']
        idx=int(re.search(r'\[(\d+)\]',p['source_record_path'])[1]); original=docs[sid]['best_model_selections'][idx]
        assert (sid,idx) not in selection_seen
        selection_seen.add((sid,idx))
        for field in p:
            if field not in {'study_id','source_record_path'}:assert p[field]==human(original.get(field)),(sid,idx,field)
    assert len(selection_seen)==sum(len(d.get('best_model_selections',[])) for d in docs.values())
    # Figure 11A and D are independently reconstructed from PUBLIC scalar rows.
    fig=json.loads((ROOT/'results/derived/figure11_reporting_probast_domain_audit.json').read_text())
    for r in fig['reporting']['items']:
        c=item_counts[r['item_id']]
        assert (c['R'],c['P'],c['NR']+c['UNC'])==(r['complete'],r['partial'],r['not_reported_or_unclear']),r
    for kind,prefix,mapping in [('development','PD',{'HIGH':'high_quality','UNC':'unclear','LOW':'low_quality'}),
                               ('evaluation','PE',{'LOW':'low_risk','UNC':'unclear','HIGH':'high_risk'})]:
        for key,label in zip(['D1','D2','D3','D4','OVERALL'],fig['probast_ai'][kind]['rows']):
            c=item_counts[prefix+'_'+key]
            assert {dest:c[src] for src,dest in mapping.items()}==fig['probast_ai'][kind]['rows'][label]
    # B uses one retained study response; check all states, not only positives.
    for key, expected in fig['survey_design_status'].items():
        assert {k:item_counts[key][k] for k in expected}==expected,(key,item_counts[key])
    core=[r for r in studies.values() if r['B_core_health_classification']=='Y']
    importance=[r for r in core if 'USED' in str(r['I_importance_reported']).split(' | ')]
    association=[r for r in core if 'POPULATION_ASSOCIATION_ANALYSIS' in str(r['B_scientific_purposes']).split(' | ')]
    assert [len(importance),len(association)]==fig['claim_evidence']['claim_present'][:2]
    assert [sum(r['M_importance_stability_support_criteria_met']=='Y' for r in importance),
            sum(r['M_population_association_support_criteria_met']=='Y' for r in association)]==fig['claim_evidence']['matched_evidence'][:2]
    app={'SCREENING','DIAGNOSTIC_SUPPORT','PERSONALISED_MANAGEMENT','RISK_GROUP_IDENTIFICATION'}
    application=[r for r in core if set(r['B_proposed_uses'].split(' | '))&app]
    policy=[r for r in core if 'POPULATION_SURVEILLANCE_OR_POLICY' in r['B_proposed_uses']]
    assert [len(application),len(policy)]==fig['claim_evidence']['claim_present'][2:]
    assert [sum(r['M_individual_application_support_criteria_met']=='Y' for r in application),
            sum(r['M_surveillance_policy_support_criteria_met']=='Y' for r in policy)]==fig['claim_evidence']['matched_evidence'][2:]
    # Analysis field corrections have actual evidence, retained history and no fake NR.
    target={'KHM011','KHM036','KHM045','KHM053','KHM081','KHM082','KHM093','KHM136','KHM204','KHM210'}
    for sid in target:
        a=docs[sid]['adjudication']['purpose_evidence_v1_3']['statistical_analysis_records'][0]
        assert a['population'] not in {'NR',None} and a['field_revisions']
        assert all(e in registry[sid] for e in a['field_evidence_ids']['population'])
    assert docs['KHM011']['adjudication']['purpose_evidence_v1_3']['statistical_analysis_records'][0]['result']!='NR'
    a=docs['KHM011']['adjudication']['purpose_evidence_v1_3']['statistical_analysis_records'][0]
    assert a['field_status']['result']=='UNCLEAR' and all(x in a['result'] for x in ('1.82','1.62','Table 2'))
    assert not any('value for ' in r['Definition'] for r in rows(w,'DATA_DICTIONARY'))
    # Every final record is retained, including any pre-existing unresolved references.
    result={'status':'PASS' if not evidence_errors and not unit_errors else 'CONTENT_REFERENCE_REMAINDERS',
            'studies':len(studies),'study_variables':w['STUDIES'].max_column,'sheets':len(w.sheetnames),
            'final_responses_compared_field_by_field':len(seen),'model_selections_compared':len(selection_seen),
            'source_records_roundtrip_equal':len(chunks),'figure11_public_reconstruction':'PASS',
            'original_unresolved_evidence_ids':evidence_errors,'original_unresolved_related_ids':unit_errors,
            'source_read_population_fields':10,'source_read_result_fields':1,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in result.items()},ensure_ascii=False,indent=2))
    w.close()
if __name__=='__main__':main()

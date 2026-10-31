"""Run inside the extracted reviewer package: python verify_delivery.py.
Requires openpyxl. Checks file bytes, source reconstruction and public-sheet counts.
It does not certify the scientific truth of source judgements.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json
from openpyxl import load_workbook
ROOT=Path(__file__).resolve().parent

def rows(w,s):
 it=iter(w[s].values);h=next(it)
 for r in it:yield dict(zip(h,r))

def main():
 manifest=json.loads((ROOT/'MANIFEST.json').read_text())
 for name,h in manifest['sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name
 a=json.loads((ROOT/'openalex_source_preprocessing.json').read_text()); c=a['counts']
 v=json.loads((ROOT/'openalex_source_input_view.json').read_text()); f=json.loads((ROOT/'selection_flow.json').read_text())
 assert len(v['records'])==len({r['oa_id'] for r in v['records']})==c['openalex_merge_inputs']==9998
 ids={r['oa_id'] for r in v['records']}
 assert len(a['pairs'])==c['source_preexcluded']==2
 for p in a['pairs']:assert p['retained_id'] in ids and p['removed_id'] not in ids
 assert c['openalex_raw']==c['openalex_merge_inputs']+c['source_preexcluded']==10000
 assert c['database_index_inputs']==16435 and c['merged_flow_inputs']==18514
 assert c['raw_source_total']==c['merged_flow_inputs']+c['source_preexcluded']==18516
 assert c['merged_flow_inputs']-c['remaining_duplicates']==c['screened']==11077
 assert c['remaining_duplicates']==f['flow']['duplicates_removed']==7437
 w=load_workbook(ROOT/'bmc_supplementary_data1.xlsx',read_only=True,data_only=True)  # prompt 097: study-level workbook is Additional Data 1
 studies={r['A_study_id']:r for r in rows(w,'STUDIES')};core={s for s,r in studies.items() if r['B_core_health_classification']=='Y'}
 assert len(studies)==250 and len(core)==192  # prompt 106: criterion A
 counts=defaultdict(Counter);responses=0
 for r in rows(w,'ITEM_RESPONSES'):
  responses+=1
  if r['study_id'] in core:counts[r['item_id']][r['final_value']]+=1
 assert counts['PD_OVERALL']==Counter({'LOW':270,'HIGH':15,'UNC':12})  # prompt 106
 assert counts['PE_OVERALL']==Counter({'HIGH':375,'LOW':2,'UNC':1,'NA':4})  # prompt 106: four core trees fitted without evaluation
 assert counts['REP06']==Counter({'R':77,'P':110,'NR':5})  # prompt 106
 topic_rows=list(rows(w,'TOPIC_CROSSWALK'));assert len(topic_rows)==214  # prompt 106
 for r in topic_rows:assert r['canonical_topic']==studies[r['study_id']]['B_health_topic']
 topics=Counter(r['canonical_topic'] for r in topic_rows)
 chunks=defaultdict(list);digests={}
 for r in rows(w,'SOURCE_JSON'):
  chunks[r['study_id']].append((int(r['chunk_index']),r['json_chunk']));digests[r['study_id']]=r['sha256_of_joined_json']
 reconstructed={}
 for sid,parts in chunks.items():
  text=''.join(v for _,v in sorted(parts));assert hashlib.sha256(text.encode()).hexdigest()==digests[sid]
  d=json.loads(text);assert d['study_id']==sid;reconstructed[sid]=d
 assert set(chunks)==set(studies)
 relation=json.loads((ROOT/'purpose_output_relationships.json').read_text())
 public={r['study_id']:r for r in rows(w,'PURPOSE_OUTPUT_STUDIES')}
 for row in public.values():
  for key,value in list(row.items()):
   if key=='study_id':continue
   assert value in ('Yes','No'),(key,value)
   row[key]=value=='Yes'
 assert len(public)==len(relation['rows'])==214  # prompt 106
 for row in relation['rows']:
  sid=row['study_id'];assert public[sid]==row
  adj=reconstructed[sid]['adjudication']; p=adj['study_category_and_dataset_use'];a=adj['purpose_evidence_v1_3']
  assert p['study_category']=='HEALTH_ANALYSIS'
  expected=[('interpretation_purpose','VARIABLE_RELEVANCE_OR_MODEL_INTERPRETATION' in p['health_analysis_purpose_components']),('importance_output','VARIABLE_CONTRIBUTION_OR_RANK' in p['analytic_outputs']),('association_purpose','POPULATION_ASSOCIATION_ANALYSIS' in p['health_analysis_purpose_components']),('association_output',a['association_audit']['any_association_estimate_reported']=='Y')]
  for key,value in expected:assert row[key]==value,(sid,key)
 summaries=list(rows(w,'PURPOSE_OUTPUT_2X2'))
 for rel,expected,summary in zip(relation['relationships'],[[79,4,85,46],[20,1,40,153]],summaries):  # prompt 106: 214 health-focused studies
  cell_counts=[]
  for label,x,y in [('both',True,True),('purpose_only',True,False),('output_only',False,True),('neither',False,False)]:
   ids=sorted(sid for sid,r in public.items() if r[rel['purpose_field']]==x and r[rel['output_field']]==y)
   assert ids==sorted(rel['study_ids'][label]);cell_counts.append(len(ids))
  assert cell_counts==expected==list(rel['counts'].values())
  assert [int(summary[k]) for k in ['Both','Purpose only','Output only','Neither']]==cell_counts
 # Full canonical metadata, with the distinct 12-item purpose/output extension.
 metadata=[json.loads(r['Canonical metadata JSON']) for r in rows(w,'PROTOCOL_CROSSWALK')]
 canonical=[m for m in metadata if len(m)==17]
 assert len(canonical)==382 and len({m['item_id'] for m in canonical})==382
 assert len(metadata)==394
 assert all(set(m)==set(canonical[0]) for m in canonical)
 # Reconstruct every Figure 11 count using only losslessly reconstructed S7 records.
 audit=json.loads((ROOT/'figure11_reporting_probast_domain_audit.json').read_text())
 docs=[reconstructed[sid] for sid in sorted(core)]
 def values(d,key):
  result=[]
  for r in d.get('protocol_items',{}).get(key,[]):
   value=r.get('value')
   result.extend(value if isinstance(value,list) else [value])
  return result
 def has(d,key,accepted):return bool(set(values(d,key)) & set(accepted))
 for item in audit['reporting']['items']:
  c=Counter(v for d in docs for v in values(d,item['item_id']))
  assert [c['R'],c['P'],c['NR']+c['UNC']]==[item['complete'],item['partial'],item['not_reported_or_unclear']]
  assert sum(c.values())==item['denominator']==192  # prompt 106
 for key,expected in audit['survey_design_status'].items():
  c=Counter((values(d,key) or ['NR'])[0] for d in docs)
  assert dict(c)=={k:v for k,v in expected.items() if v},key
 for section,prefix,states in [('development','PD',['HIGH','UNC','LOW']),('evaluation','PE',['LOW','UNC','HIGH'])]:
  part=audit['probast_ai'][section]
  for label,key in zip(part['rows'],[f'{prefix}_D{i}' for i in range(1,5)]+[f'{prefix}_OVERALL']):
   c=Counter(v for d in docs for v in values(d,key) if v!='NA')
   assert [c[k] for k in states]==list(part['rows'][label].values()),(section,label)
   assert sum(c.values())==part['unit_n']
 def purpose(d):return d['adjudication']['study_category_and_dataset_use']
 groups=[ [d for d in docs if has(d,'VI01',{'USED'})],
          [d for d in docs if 'POPULATION_ASSOCIATION_ANALYSIS' in purpose(d)['health_analysis_purpose_components']],
          [d for d in docs if set(purpose(d)['proposed_use']) & {'SCREENING','DIAGNOSTIC_SUPPORT','PERSONALISED_MANAGEMENT','RISK_GROUP_IDENTIFICATION'}],
          [d for d in docs if 'POPULATION_SURVEILLANCE_OR_POLICY' in purpose(d)['proposed_use']] ]
 criteria=[lambda d:has(d,'VI16',{'USED'}),
           lambda d:d['adjudication']['purpose_evidence_v1_3']['association_audit']['population_association_was_survey_aware']=='Y',
           lambda d:has(d,'VAL02',{'EXTERNAL','TEMPORAL'}) and any(has(d,k,{'R'}) for k in ['MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R']) and has(d,'THR01',{'FIXED05','YOUDEN','VAL_OOF','F1','CLINICAL','OTHER'}),
           lambda d:has(d,'SUR04',{'USED'}) and any(has(d,k,{'USED'}) for k in ['SUR08','SUR09','SUR10'])]
 assert [len(g) for g in groups]==audit['claim_evidence']['claim_present']
 assert [sum(fn(d) for d in g) for fn,g in zip(criteria,groups)]==audit['claim_evidence']['matched_evidence']
 assert audit['claim_evidence']['matched_evidence'][2]==5 and len(groups[2])==65  # prompt 106: individual-use claims 48 -> 65
 assert len(list(rows(w,'EVIDENCE_ANCHORS')))>0 and len(list(rows(w,'RECORD_EVIDENCE')))>0
 rechecks=json.loads((ROOT/'kci_fulltext_rechecks.json').read_text())
 assert len(rechecks['records'])==2 and not f['terminology_screen']['unresolved_fulltext_recheck_uids']
 assert rechecks['records']==f['terminology_screen']['resolved_fulltext_rechecks']
 assert {r['current_status'] for r in rechecks['records']}=={'EXCLUDE_NO_DIRECT_KNHANES_ANALYSIS','EXCLUDE_NO_ELIGIBLE_ML'}
 assert len(list(rows(w,'DECLARED_AMENDMENTS')))==2
 # Figure 12: every period value (including intermediate periods) from S7 only.
 temporal=json.loads((ROOT/'figure12_temporal_practice_analysis.json').read_text())['health_focused_classification']
 periods=['≤2019','2020–2022','2023–2024','2025–2026']
 def period(y):return periods[0] if y<=2019 else periods[1] if y<=2022 else periods[2] if y<=2024 else periods[3]
 groups12={p:[d for d in docs if period(int(studies[d['study_id']]['A_publication_year']))==p] for p in periods}
 assert [len(groups12[p]) for p in periods]==temporal['period_denominators']==[45,35,59,53] and sum(temporal['period_denominators'])==192  # prompt 106
 def fam(d,names):
  raw=studies[d['study_id']]['G_algorithm_families'];vals=set() if raw in (None,'NR') else set(raw.split(' | '))
  return bool(vals&names)
 def recov(d,key):
  v=set(values(d,key));return 'NO' if 'R0' in v else 'PART' if 'R1' in v else 'FULL' if 'R2' in v else 'NO'
 specs={'interpretation_practices':{'Algorithm comparison':lambda d:has(d,'FUN_COMPARE',{'PRESENT'}),'Model-based importance':lambda d:has(d,'VI01',{'USED'}),'SHAP':lambda d:has(d,'VI02',{'SHAP'}),'Stability assessed':lambda d:has(d,'VI16',{'USED'})},
  'algorithm_families':{'Tree-based boosting':lambda d:fam(d,{'XGBoost','LightGBM','Gradient boosting'}),'Random forest':lambda d:fam(d,{'Random forest'}),'Logistic regression':lambda d:fam(d,{'Logistic regression'}),'SVM':lambda d:fam(d,{'SVM'}),'Neural networks':lambda d:fam(d,{'DNN/MLP'})},
  'validation_evidence':{'Later/external validation':lambda d:has(d,'VAL02',{'EXTERNAL','TEMPORAL'}),'Calibration reported':lambda d:any(has(d,k,{'R'}) for k in ['MET_CALSLOPE_R','MET_CALINT_R','MET_CALPLOT_R']),'Paired model comparison':lambda d:has(d,'MET_PAIR',{'Y','USED'})},
  'reproducibility_and_survey_reporting':{'Candidate predictors specified':lambda d:recov(d,'PRD13')=='FULL','Tuning/evaluation separated':lambda d:studies[d['study_id']]['G_hyperparameter_search']=='TUNING_REPORTED_SEPARATED','Final model fully specified':lambda d:has(d,'REP17',{'R'}),'Analysis code available':lambda d:has(d,'MOD15',{'USED'}),'Survey weights reported':lambda d:has(d,'SUR04',{'USED'})}}
 fig12_values=0
 for panel,series in specs.items():
  assert set(series)==set(temporal[panel]),panel
  for name,fn in series.items():
   for p in periods:
    assert sum(fn(d) for d in groups12[p])==temporal[panel][name][p]['n'],(panel,name,p);fig12_values+=1
 assert fig12_values==68
 result={'status':'PASS' ,'scope':'Byte integrity, 250 lossless source reconstructions, public scalar response counts and topic agreement; not independent confirmation of every source judgement','canonical_protocol_items':382,'canonical_metadata_fields':17,'figure11_all_panels_reconstructed':True,'figure12_period_values_reconstructed':fig12_values,'studies':len(studies),'core':len(core),'item_responses':responses,'source_records':len(chunks),'purpose_output_counts':[list(r['counts'].values()) for r in relation['relationships']],'resolved_kci_rechecks':2,'development':dict(counts['PD_OVERALL']),'evaluation':dict(counts['PE_OVERALL']),'REP06':dict(counts['REP06']),'topics':dict(topics),'declared_amendments':len(list(rows(w,'DECLARED_AMENDMENTS'))),'bounded_source_cases':len(list(rows(w,'SOURCE_REASSESSMENT')))}
 print(json.dumps(result,indent=2));w.close()
if __name__=='__main__':main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)

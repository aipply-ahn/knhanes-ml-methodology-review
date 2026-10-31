"""Verify the declared source-preprocessing basis without weakening raw-data checks."""
import re
from pathlib import Path
import hashlib,json,unittest
ROOT=Path(__file__).resolve().parents[1]
AUDIT=ROOT/'prompts/implementation_records/openalex_source_dedup'
def load(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
from revision_artifact_checks import current_amendments, assert_amendment, current  # prompt 119
class SourcePreprocessing(unittest.TestCase):
 def test_protected_bytes_and_backup(self):
  amendments=load(str(AUDIT.relative_to(ROOT)/'asset_amendments.json'))
  for p,h in load(str(AUDIT.relative_to(ROOT)/'protected_sha256.json')).items():
   if p in current_amendments():
    assert_amendment(self,p,h)
   elif p in amendments:
    self.assertEqual(sha(AUDIT/'before'/p),h,p)
    self.assertEqual(amendments[p]['before_sha256'],h,p)
    self.assertEqual(sha(ROOT/current(p)),amendments[p]['after_sha256'],p)
   else:self.assertEqual(sha(ROOT/current(p)),h,p)
  self.assertEqual(sha(ROOT/'results/derived/figure11_reporting_probast_domain_audit.json'),json.loads((ROOT/'prompts/implementation_records/prompt_106/artifact_amendments.json').read_text())['results/derived/figure11_reporting_probast_domain_audit.json']['after_sha256'])  # Prompt 106
  manifest=load(str(AUDIT.relative_to(ROOT)/'before_sha256.json'))
  self.assertEqual(set(manifest),{str(p.relative_to(AUDIT/'before')) for p in (AUDIT/'before').rglob('*') if p.is_file()})
  for p,h in manifest.items():self.assertEqual(sha(AUDIT/'before'/p),h,p)
 def test_view_membership_and_mapping(self):
  raw=load('results/raw/openalex_20260905.json')['records'];v=load('results/derived/openalex_source_input_view.json')
  a=load('results/derived/openalex_source_preprocessing.json');c=a['counts'];pairs=a['pairs']
  removed={p['removed_id'] for p in pairs};keep={p['retained_id'] for p in pairs}
  self.assertEqual(removed,{'https://openalex.org/W4225324040','https://openalex.org/W4221046485'})
  self.assertEqual(v['records'],[r for r in raw if r['oa_id'] not in removed])
  self.assertTrue(keep <= {r['oa_id'] for r in v['records']})
  legacy=load('prompts/implementation_records/openalex_recount/legacy_merge_mapping.json')
  mapping={r['oa_id']:r['target_uid'] for r in legacy if r['source']=='OpenAlex'}
  corpus={r['uid']:r for r in load('results/derived/corpus.json')['records']}
  for p in pairs:
   self.assertEqual(mapping[p['removed_id']],mapping[p['retained_id']]);self.assertEqual(corpus[p['corpus_uid']]['oa_id'],p['retained_id'])
  self.assertEqual(c['openalex_raw'],len(raw));self.assertEqual(c['openalex_merge_inputs'],len(v['records']))
  self.assertEqual(c['raw_source_total'],18516);self.assertEqual(c['database_index_inputs'],16435)
  self.assertEqual(c['merged_flow_inputs']+len(removed),c['raw_source_total'])
  self.assertEqual(c['merged_flow_inputs']-c['remaining_duplicates'],11077)
  self.assertEqual(c['remaining_duplicates'],7437);self.assertEqual(c['candidates'],1499)  # source-preprocessing record (historical view)  # Prompt 106
 def test_only_declared_flow_changes(self):
  old=json.loads((AUDIT/'before/results/derived/final_selection_flow.json').read_text());new=load('results/derived/final_selection_flow.json')
  NEW106={'terminology_exclusions':9562,'records_assessed_against_eligibility':1515,'reports_excluded_total':1239,'ineligible_reports':1142,'ml_adjacent_reports_catalogued':97,'eligible_reports_entering_family_linkage':276,'additional_or_companion_reports_linked':26,'unique_full_report_studies_included':250,'report_exclusion_reasons':{'no_eligible_machine_learning':404,'not_knhanes':352,'review_or_non_primary_synthesis':199,'no_eligible_knhanes_analysis':81,'abbreviation_false_positive':15,'other_or_unassessable':91,'ml_adjacent_catalogued_separately':97}}  # Prompt 106
  self.assertEqual(old['flow']['duplicates_removed']-new['flow']['duplicates_removed'],2)
  for k,v in old['flow'].items():
   if k!='duplicates_removed' and k not in NEW106:self.assertEqual(new['flow'][k],v)
  for k,v in NEW106.items():self.assertEqual(new['flow'][k],v,k)  # Prompt 106
  self.assertEqual(old['full_text_retrieval'],new['full_text_retrieval'])
  # Current full-text overlay resolves exactly the two old KCI rechecks.
  overlay=load('results/derived/kci_fulltext_rechecks.json')
  before=dict(old['terminology_screen']);after=dict(new['terminology_screen'])
  self.assertEqual(after.pop('resolved_fulltext_rechecks'),overlay['records'])
  self.assertEqual(after.pop('current_recheck_source'),'results/derived/kci_fulltext_rechecks.json')
  self.assertEqual(after['unresolved_fulltext_recheck_uids'],[])
  self.assertEqual(after['interpretation'],overlay['scope'])
  self.assertEqual({r['uid'] for r in overlay['records']},set(before['unresolved_fulltext_recheck_uids']))
  for key in ('unresolved_fulltext_recheck_uids','interpretation'):after[key]=before[key]
  self.assertEqual(after['partition']['no_dictionary_signal'],9562);self.assertEqual(after['partition']['kci_not_advanced'],0)
  after['partition']=dict(after['partition'],no_dictionary_signal=before['partition']['no_dictionary_signal'],kci_not_advanced=before['partition']['kci_not_advanced'])  # Prompt 106
  self.assertEqual(before,after)
  for p in ('manuscript/bmc_main.tex','manuscript/bmc_main_ko.tex'):
   before=(AUDIT/'before'/p.replace('manuscript/','paper/',1)).read_text();after=(ROOT/p).read_text()
   self.assertEqual(before.split('\\begin{document}')[0],after.split('\\begin{document}')[0])
 def test_final_pdf_counts(self):
  import fitz
  for p in ('figures/submission/fig1_prisma.pdf','figures/submission/fig1_prisma_ko.pdf','manuscript/bmc_main.pdf','manuscript/bmc_main_ko.pdf'):
   with fitz.open(ROOT/p) as d:t=' '.join(x.get_text() for x in d)
   for n in ('9,998','16,435','18,514','7,437','11,077'):self.assertIn(n,t,p)
  with fitz.open(ROOT/'manuscript/bmc_supplementary.pdf') as d:t=' '.join(' '.join(x.get_text() for x in d).split()).replace('\u2011','-')
  # Prompt 093 (review v31 section 3.2) removed the work-ID reallocation note from Table S3; the two removed
  # same-DOI pairs are still stated there, and the IDs and the 18,516 raw total stay in the delivered audit JSON.
  t=re.sub(r'(\w)- (\w)',r'\1\2',t)  # Prompt 096 (review v34): join words hyphenated at a line break ("re- moved")
  for n in ('9,998','7,437','10,000','Two same-DOI duplicate pairs were removed'):self.assertIn(n,t)
  a=load('results/derived/openalex_source_preprocessing.json')
  self.assertEqual(a['counts']['raw_source_total'],18516)
  self.assertEqual({p['removed_id'] for p in a['pairs']},{'https://openalex.org/W4225324040','https://openalex.org/W4221046485'})
if __name__=='__main__':unittest.main()

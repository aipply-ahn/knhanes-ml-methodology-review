"""Build the actual reviewer delivery, not a manifest pointing outside it."""
from pathlib import Path
import hashlib,json,shutil,zipfile
ROOT=Path(__file__).resolve().parents[1]

def main():
 out=ROOT/'manuscript/reviewer_delivery';out.mkdir(exist_ok=True)
 sources={n:ROOT/'manuscript'/n for n in ['bmc_main.pdf','bmc_main_ko.pdf','bmc_supplementary.pdf','bmc_supplementary_data1.xlsx']}
 sources.update({'verify_delivery.py':ROOT/'tools/verify_review_delivery.py','topic_crosswalk.tsv':ROOT/'data/protocol_v1_3/topic_crosswalk.tsv','source_reassessment.json':ROOT/'data/protocol_v1_3/judgement_reassessment.json','topic_adjudications.json':ROOT/'data/protocol_v1_3/topic_adjudications.json'})
 sources.update({'selection_flow.json':ROOT/'results/derived/final_selection_flow.json', 'openalex_source_preprocessing.json':ROOT/'results/derived/openalex_source_preprocessing.json', 'openalex_source_input_view.json':ROOT/'results/derived/openalex_source_input_view.json'})
 sources.update({'purpose_output_relationships.json':ROOT/'results/derived/purpose_output_relationships.json','purpose_output_relationships.tsv':ROOT/'results/derived/purpose_output_relationships.tsv','kci_fulltext_rechecks.json':ROOT/'results/derived/kci_fulltext_rechecks.json'})
 sources['figure11_reporting_probast_domain_audit.json']=ROOT/'results/derived/figure11_reporting_probast_domain_audit.json'
 sources['figure12_temporal_practice_analysis.json']=ROOT/'results/derived/exploratory_temporal_practice_analysis.json'
 # Prompt 094: the claim-evidence framing was removed; the period and practice counts behind Figures 3, 4 and 6 ship instead.
 sources.update({n:ROOT/'paper'/n for n in ('KNHANES_ML_review_Main.pdf','KNHANES_ML_review_Supplementary.pdf','KNHANES_ML_review_Additional_Data_1.xlsx')})  # Prompt 115: the three submission files; bmc_supplementary_data1.xlsx is the full coding log
 sources['practice_trends.json']=ROOT/'results/derived/practice_trends_112.json'  # Prompt 106: criterion A values (literature map, ranking domains); Prompt 108: superset
 for name,p in sources.items():shutil.copy2(p,out/name)
 # Prompt 093: two submission files (Additional file 1 = supplement PDF, Additional file 2 = Table S5 workbook).
 for stale in ('bmc_supplementary_table_s5.xlsx','bmc_supplementary_table_s7.xlsx','bmc_supplementary_table_s9.xlsx','bmc_supplementary_table_s10.xlsx','claim_evidence_synthesis.json'):
  if (out/stale).exists():(out/stale).unlink()
 readme='''# Reviewer delivery\n\nRead bmc_main.pdf (English) or bmc_main_ko.pdf (Korean). Each carries the English supplement (Additional file 1) after its reference list, one table or figure per page; bmc_supplementary.pdf is the same supplement on its own. Supplementary items are numbered in the order the main text cites them; Tables S6 and S7 are the human verification protocol and its recorded results, and S8 lists the included studies (10 of 220 at present).\n\nbmc_supplementary_data1.xlsx (Additional file 2) is Supplementary Data 1, the study-level dataset. Start with STUDIES and VARIABLE_DICTIONARY. ML_ADJACENT_REPORTS lists the 134 ML-adjacent reports; PROTOCOL_ITEMS and PROTOCOL_RESPONSE_CODES give all 306 coding items; the ASSESSMENT_ sheets give readable study-level assessments. ITEM_RESPONSES keeps every response with its evidence IDs, and SOURCE_JSON reconstructs all included source records losslessly.\n\nRun `python verify_delivery.py` (requires openpyxl). It checks byte integrity, reconstruction and counts, not the truth of every judgement. No public repository deposit is claimed by this local delivery.\n'''
 readme += '\nSelection-flow counts: raw OpenAlex 10,000 IDs minus two same-DOI duplicate records = 9,998 records entering deduplication; 18,514 records before deduplication, 7,437 duplicates removed, 11,077 screened. The two DOI pairs are in openalex_source_preprocessing.json. kci_fulltext_rechecks.json records the two full-text checks that confirmed ineligibility.\n'
 readme += '\nThe verifier reconstructs the reporting, survey-design and PROBAST+AI counts (Supplementary Figure S7 and Figure 5B) and 68 period values of the earlier period audit from the workbook (the packaged audit files keep earlier figure numbers in their names). practice_trends.json gives the counts behind Figures 2 to 6, Supplementary Figures S1 and S3E and Table 1, including the study-level literature map and the domains named by each ranking. purpose_output_relationships.json/tsv are retained record-level outputs; authors\' aims and proposed uses are not used in the manuscript.\n'
 readme += '\nSubmission files: KNHANES_ML_review_Main.pdf (manuscript), KNHANES_ML_review_Supplementary.pdf (Additional file 1) and KNHANES_ML_review_Additional_Data_1.xlsx (Additional file 2, Additional Data 1: start with Columns and Reproduce; Studies has one row per study). bmc_supplementary_data1.xlsx is the internal full coding log behind it (not submitted).\n'
 (out/'README.md').write_text(readme)
 names=sorted([*sources,'README.md'])
 manifest={'schema':'reviewer_delivery_v1','sha256':{n:hashlib.sha256((out/n).read_bytes()).hexdigest() for n in names}}
 (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
 zip_path=ROOT/'manuscript/reviewer_delivery.zip'
 with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
  for name in [*names,'MANIFEST.json']:z.write(out/name,name)
 with zipfile.ZipFile(zip_path) as z:
  assert set(z.namelist())==set(names)|{'MANIFEST.json'}
  for n,h in manifest['sha256'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
 print(json.dumps({'package':str(zip_path.relative_to(ROOT)),'files':len(names)+1,'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest()},indent=2))
if __name__=='__main__':main()

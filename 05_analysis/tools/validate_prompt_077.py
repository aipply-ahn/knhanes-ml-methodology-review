#!/usr/bin/env python3
"""Delivered-file regression checks for prompt 077; no network or source mutation."""
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import fitz
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'prompts/implementation_records/prompt_077'
TABLES = ROOT / 'manuscript/supplementary/tables'

# Prompt 093: the study-level workbook is Supplementary Table S5; dictionary and 306-item protocol are its sheets.
S5WB = TABLES / 'Supplementary_Data_1_Study_level_dataset.xlsx'  # Prompt 097: workbook renamed Additional Data 1

def rows(path, sheet=None):
    wb = load_workbook(path, read_only=True, data_only=True)
    data = list((wb[sheet] if sheet else wb.active).values)
    wb.close()
    return data

def main():
    checks = {}
    s2 = rows(S5WB, 'PROTOCOL_ITEMS')  # prompt 093: 306-item instrument is a Table S5 sheet (was Table S9)
    items = {r[0]:r for r in s2[1:] if r[1]}
    checks['english_s2_all_cells'] = not re.search('[가-힣]', str(s2))
    checks['306_items_7_columns'] = len(items) == 306 and len(s2[0]) == 7
    keys = ['ELG04','FAM03','VAL07','VI01','VI16'] + [f'SUR{i:02d}' for i in range(4,12)]
    checks['priority_boundaries_explicit'] = all('NR=' in items[k][5] if k not in {'ELG04','FAM03'}
                                                else 'Y=' in items[k][5] and 'N=' in items[k][5] for k in keys)
    checks['positive_analysis_linkage_conditional'] = all('required for a directly linked Y' in items[k][2]
                                                       and 'missing linkage=UNCLEAR' in items[k][2] for k in ('ASSOC01','ASSOC02','ASSOC03'))
    checks['legacy_evaluation_not_treated_as_nonuse'] = 'unresolved evaluation status' in items['VAL02'][5]
    s5 = rows(S5WB, 'VARIABLE_DICTIONARY')  # prompt 093: cell-identical to the former S5 dictionary
    d = {r[0]:r for r in s5[1:]}
    s7path = S5WB
    s7 = rows(s7path, 'STUDIES')
    studies = [dict(zip(s7[0],r)) for r in s7[1:]]
    checks['158_columns_same_order_220_unique_ids'] = ([r[0] for r in s5[1:]] == list(s7[0])
        and len(s7[0]) == 158 and len(studies) == len({r['A_study_id'] for r in studies}) == 250)  # prompt 106
    checks['missingness_labels_correct'] = all(x in d['F_missing_data_method'][5] for x in
        ('NONE=No missing values/handling unnecessary','COMPLETE=Complete-case/listwise deletion','MULTIPLE=Multiple methods'))
    checks['rebalancing_classification_only'] = ('Classification studies only' in d['F_class_rebalancing'][4]
        and all(r['F_class_rebalancing'] == 'NA' for r in studies if r['B_analytic_task'] != 'CLASSIFICATION'))
    checks['rebalancing_labels_complete'] = all(x in d['F_class_rebalancing'][5] for x in
        ('ALGO=Algorithm-specific method','MULTIPLE=Multiple strategies','NONE=','NR='))
    checks['study_id_required_not_missing'] = 'not permitted' in d['A_study_id'][5] and 'Required' in d['A_study_id'][5]
    technical = {r[0]:r for r in rows(s7path,'DATA_DICTIONARY')[1:]}
    checks['all_purpose_output_use_codes_labelled'] = all(
        all(code.strip()+'=' in d[key][5] for code in technical[key][6].split('|'))
        for key in ('B_scientific_purposes','B_analytic_outputs','B_proposed_uses'))
    checks['no_specific_use_remains_derived'] = 'not an input code' in d['B_proposed_uses'][5] and 'NO_SPECIFIC_USE' not in items['USE01'][4]
    detailed = rows(s7path,'RECORD_DETAILS')[1:]
    byid = {r[1]:r for r in detailed}
    linked = rows(s7path,'RECORD_EVIDENCE')[1:]
    link_ids = {r[1] for r in linked if r[4] == 'RESOLVED'}
    sources = json.loads((ROOT/'data/protocol_v1_3/purpose_evidence_addendum.json').read_text())['records']
    improvement_ok = []; analysis_ok = []; source_ok = []
    for source in sources:
        sid = source['study_id']
        doc = json.loads((ROOT/f'data/protocol_v1_2/final/{sid}_final.json').read_text())
        source_ok.append(doc['adjudication']['purpose_evidence_v1_3'] == source)
        if source['primary_orientation'] == 'METHOD_FOCUSED':
            value = source['method_research']['improvement_evidence']
            public = byid[f'{sid}-METHOD-IMPROVEMENT_EVIDENCE-001']
            improvement_ok.append(public[3] == value and 'target method:' in public[8]
                                  and 'comparators:' in public[8] and public[1] in link_ids)
        for a in source.get('statistical_analysis_records',[]):
            public = byid[a['statistical_analysis_id']]
            stored = json.loads(public[13])
            required = {'study_id','statistical_analysis_id','population','outcome','model_or_contrast',
                        'result','field_status','description','evidence_ids','note'}
            analysis_ok.append(required <= a.keys() and all(stored[k] == v for k,v in a.items())
                and public[1] in link_ids and all(k+':' in public[8] for k in ('population','outcome','model_or_contrast','result')))
    checks['canonical_and_addendum_equal'] = all(source_ok)
    checks['36_improvement_values_methods_evidence_preserved'] = len(improvement_ok) == 36 and all(improvement_ok)
    checks['21_analysis_records_structured_and_preserved'] = len(analysis_ok) == 21 and all(analysis_ok)
    health = [s for s in studies if s['B_primary_orientation'] == 'HEALTH_FOCUSED']
    outputs = Counter(c for r in health for c in r['B_analytic_outputs'].split(' | '))
    uses = Counter(c for r in health for c in r['B_proposed_uses'].split(' | '))
    checks['figure3_source_counts_unchanged'] = outputs['MODEL_PERFORMANCE'] == 200 and outputs['ASSOCIATION_ESTIMATE'] == 60 and uses['OTHER'] == 2  # prompt 106
    core = [s for s in health if s['B_core_health_classification'] == 'Y']
    app = {'SCREENING','DIAGNOSTIC_SUPPORT','PERSONALISED_MANAGEMENT','RISK_GROUP_IDENTIFICATION'}
    application = [r for r in core if set(r['B_proposed_uses'].split(' | ')) & app]
    policy = [r for r in core if 'POPULATION_SURVEILLANCE_OR_POLICY' in r['B_proposed_uses'].split(' | ')]
    checks['figure11_denominators_reproduced_from_s7'] = len(core) == 192 and len(application) == 65 and len(policy) == 48  # prompt 106
    checks['figure11_numerators_reproduced_from_s7'] = (sum(r['M_individual_application_support_criteria_met']=='Y' for r in application)==5
        and sum(r['M_surveillance_policy_support_criteria_met']=='Y' for r in policy)==15)  # prompt 106
    pdf = fitz.open(ROOT/'manuscript/bmc_main.pdf')
    texts = [unicodedata.normalize('NFKC',' '.join(p.get_text().split())) for p in pdf]
    # Prompt 093: the purpose/output panels are Fig. 2 "How machine learning was used and what studies claimed"
    # and must appear before the next section, "Evidence for the Classification Claim".
    pdf = fitz.open(ROOT/'build/submission/bmc_main.pdf')
    texts = [unicodedata.normalize('NFKC',' '.join(p.get_text().split())) for p in pdf]
    # Prompt 094 (review v32): Fig. 2 is "How machine learning was used with KNHANES"; the next section opens with the
    # explanation finding, so the figure must sit on or before that paragraph's page.
    # Prompt 097 (review v35): Fig. 2 is the literature map.
    fig3 = next(i for i,t in enumerate(texts) if 'Fig. 3 How the 192 core studies were analysed' in t)  # Prompt 100: workflow figure; Figure 3 since prompt 107  # Prompt 107
    heading = next(i for i,t in enumerate(texts) if 'Variable Importance as the Main Product' in t)  # Prompt 100: section heading
    checks['figure3_before_complete_following_paragraph'] = (fig3 <= heading and 'SHAP' in ' '.join(texts[heading:heading+2]))
    checks['public_protocol_scope_precise'] = any('full protocol has not been publicly deposited' in t for t in texts)
    fig11_doc = fitz.open(ROOT/'figures/submission/fig11_methodological_appraisal.pdf')
    f11 = ' '.join(fig11_doc[0].get_text().split())
    checks['figure11_titles_use_cohort_rows_use_units'] = f11.count('(N=192 studies)') == 4 and 'Eligible N varies by row' not in f11 and 'Development models (n=297)' in f11 and 'Evaluations (n=378)' in f11 and '270/297 (91%)' in f11 and '375/378 (99%)' in f11  # prompt 106
    fig9_doc = fitz.open(ROOT/'figures/submission/fig9_validation_evaluation.pdf')
    f9 = ' '.join(fig9_doc[0].get_text().split())
    checks['figure9_unclear_status_visible'] = 'Evaluation status unclear' in f9
    checks['no_supplement_overflow'] = not re.search(r'Overfull \\[hv]box', (ROOT/'build/submission/bmc_supplementary.log').read_text())
    checks['s7_delivery_copy_identical'] = s7path.read_bytes() == (ROOT/'manuscript/bmc_supplementary_data1.xlsx').read_bytes()  # Prompt 097
    OUT.mkdir(parents=True,exist_ok=True)
    result = {'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,
              'counts':{'passed':sum(checks.values()),'total':len(checks)},
              'figure3_page':fig3+1,'following_heading_page':heading+1,
              'sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                        [ROOT/'KNHANES_ML_study_audit_protocol.md',ROOT/'manuscript/bmc_main.pdf',ROOT/'manuscript/bmc_main_ko.pdf',
                         ROOT/'manuscript/bmc_supplementary.pdf',s7path]}}
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert result['status'] == 'PASS'

if __name__ == '__main__':
    main()
# prompt 115: repinned to the sentences revised for review v51 (update_historical_tests.py)

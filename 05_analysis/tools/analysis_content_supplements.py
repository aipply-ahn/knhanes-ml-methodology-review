"""Source-read field supplements, not recoding of locked protocol responses."""
import copy

# Population eligibility is distinguished from an analysis-specific denominator.
# Evidence excerpts/locations are installed by apply_prompt_079_content.py.
POPULATIONS = {
 'KHM011': 'Korean adults aged at least 19 years, KNHANES 2008-2013, with blood-pressure, blood-cadmium and questionnaire data; the study reports 11,530 eligible adults. This record concerns fully adjusted model 2, not the ANN evaluation split.',
 'KHM036': 'Male workers with type 2 diabetes in KNHANES 2017-2020; the study cohort comprised 1,012 workers. The coefficient-producing linear regression is the relevant analysis; a separate regression-specific n is not stated.',
 'KHM045': 'Postmenopausal women with a history of delivery and complete gravidity, breastfeeding and biochemical data, KNHANES 2010-2020; the study cohort comprised 15,946 women. Figure 2 compares no breastfeeding with breastfeeding for less than 12 months; this is not an ML test-set estimate.',
 'KHM053': 'Community-dwelling South Korean adults without diagnosed diabetes, excluding pregnant women, KNHANES 2020. The paper reports a 3,019-person cohort but inconsistent age bounds (abstract: at least 30 and under 60; Methods: 30-65). Table 2 is the logistic analysis using CatBoost-selected factors; age ambiguity is retained, not silently resolved.',
 'KHM081': 'KNHANES 2014-2017 participants with accelerometer recordings meeting at least 10 hours/day for seven consecutive days (study cohort 1,036). This record concerns EQ-5D correlations in Table 3; do not substitute the PHQ-9 subset denominator for EQ-5D.',
 'KHM082': 'Adults aged at least 19 years in KNHANES 2019-2021 with observed activity limitation and complete predictor data (15,587 complete cases). Table 5 is the primary complex-survey regression excluding self-rated health, not the sensitivity model including it.',
 'KHM093': 'Adults aged at least 19 years with observed PHQ-9 and complete included covariates in KNHANES 2014, 2016, 2018, 2020 and 2022 (study cohort 24,308). Table 3 is the reported logistic association analysis, not an independently inferred ML evaluation subset.',
 'KHM136': 'Women aged at least 20 years in KNHANES 2010-2019, after the reported clinical-data exclusions (study cohort 30,204). Supplementary Material 2 is the obstetric-characteristic multivariable logistic analysis; its own complete-case n and restriction to parous women are not separately stated and are not inferred from the overall cohort.',
 'KHM204': 'Women aged 15-49 years in KNHANES 2007-2020, compared by current pregnancy and weekly working hours. The study describes age/birth-year propensity matching; the overall 22,731-person cohort must not be substituted for the unreported Table 5 analysis-specific n or assumed matching membership.',
 'KHM210': 'KNHANES 2015-2016 adults in the older-adult analytic cohort (5,749 after exclusions). The paper describes age as over 50 in Data Source and 50 years and older in Methods; Table 2 initial-feature correlations do not explicitly identify the full versus training-only denominator, so neither is inferred.',
}

def supplement_analysis(analysis, sid):
    if sid not in POPULATIONS or analysis.get('statistical_analysis_id') != sid+'-SA01':
        return analysis
    if not any(r.get('revision_id') == 'P079-SOURCE-FIELDS' for r in analysis.get('field_revisions', [])):
        old = copy.deepcopy(analysis)
        analysis.setdefault('field_revisions', []).append({
            'revision_id': 'P079-SOURCE-FIELDS', 'previous_record': old,
            'reason': 'Source-read population/result supplementation; no locked item or analysis identity changed.'})
    analysis['population'] = POPULATIONS[sid]
    analysis.setdefault('field_status', {})['population'] = 'REPORTED'
    analysis.setdefault('extraction_status', {})['population'] = 'SOURCE_REVIEWED'
    analysis.setdefault('field_evidence_ids', {})['population'] = [sid+'-EV980']
    analysis['evidence_ids'] = list(dict.fromkeys(analysis.get('evidence_ids', [])+[sid+'-EV980']))
    if sid == 'KHM011':
        analysis['result'] = 'Model 2, highest versus lowest blood-cadmium tertile: Results prose reports adjusted OR 1.82 (95% CI 1.17-2.83), whereas Table 2 reports 1.62 (1.38-1.92); both give p for trend <0.001. Source-internal conflict verified on PDF page 4 (printed 339); neither estimate is silently preferred.'
        analysis['field_status']['result'] = 'UNCLEAR'
        analysis['extraction_status']['result'] = 'SOURCE_REVIEWED'
        analysis['field_evidence_ids']['result'] = [sid+'-EV036',sid+'-EV043',sid+'-EV981']
        analysis['evidence_ids'] = list(dict.fromkeys(analysis['evidence_ids']+[sid+'-EV981']))
    analysis['schema_note'] = ('Field-specific source supplements retain the earlier record in field_revisions. '
        'REPORTED population text may retain explicitly stated limits; study-cohort n is not an inferred analysis n. '
        'NR means source-reviewed nonreporting, not failure to split a short description.')
    return analysis

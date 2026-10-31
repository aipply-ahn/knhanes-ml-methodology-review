"""Lossless field migration of already identified statistical analyses.

Only split information explicitly present in existing reviewed descriptions.
Unextracted fields have null value/status and extraction_status=PENDING.
"""
from analysis_content_supplements import supplement_analysis, POPULATIONS
ANALYSES = dict(line.split('|', 1) for line in """
KHM001|Adults;CKD;Logistic regression with seven boosting-selected variables;Table 4
KHM006|KNHANES analytic population;MI–CKD–anemia phenotype;Survey-weighted logistic regression of DII;OR 1.19 (95% CI 1.10–1.29)
KHM008|Women;High ASCVD risk;Multivariable logistic regression of dynapenia;OR 1.47 (95% CI 1.20–1.81)
KHM011|NR;Hypertension;Model 2 fully adjusted logistic regression of cadmium exposure;NR
KHM027|Male participants;Hypertension;Binary logistic regression of waist-to-height ratio;Table 3
KHM036|NR;Glycemic control;Linear regression of associated factors;Figure 1 coefficients
KHM038|Survey-weighted analytic groups;HOMA-IR quartiles and diabetes status;Rao–Scott chi-square comparison;Table 2, p<0.01
KHM045|NR;Diabetes mellitus;Adjusted association of no breastfeeding;Figure 2, aOR 1.29 (95% CI 1.02–1.62)
KHM053|NR;Impaired fasting glucose;Logistic regression with CatBoost-selected factors;Table 2
KHM081|NR;Quality of life (EQ-5D);Correlation with circadian activity measures;Table 3
KHM082|NR;Activity limitation;Multivariable logistic regression excluding self-rated health;Table 5
KHM093|NR;Depression;Logistic regression;Table 3 odds ratios
KHM101|Men;Suicidal ideation;Logistic association of daily/social activity restrictions;Table 2, OR 6.10 (95% CI 3.99–9.34)
KHM113|Replacement drivers and paid workers;Depressive symptoms;Fully adjusted logistic comparison of replacement drivers with paid workers;aOR 7.89
KHM136|NR;Metabolic syndrome;Multivariate logistic regression including obstetric characteristics;Supplementary Materials 2
KHM147|Younger men;Serum HDL cholesterol;Model 2 linear association with serum 25(OH)D;Table 3, beta 0.067 (SE 0.022)
KHM169|All participants;Overall body-weight misperception;Multivariable logistic regression;Figure 2
KHM202|Normal radiographs, K-L grade 0–1, N=3173;Knee pain;Multivariate logistic regression;Table 3
KHM204|NR;Pregnancy;Logistic comparison of 40–45 weekly working hours versus hours outside that range;Table 5, OR 2.009
KHM210|NR;Osteoarthritis;Correlations of initial features;Table 2
KHM220|Lowest-household-income group;Allergic disease;Logistic comparison of girls with boys;Table 7, OR 3.075
""".strip().splitlines())

def normalise_analysis_records(record):
    sid = record['study_id']
    for analysis in record.get('statistical_analysis_records', []):
        analysis.setdefault('study_id', sid)
        # Do not apply the SA01 migration to a future second analysis.
        if sid in ANALYSES and analysis['statistical_analysis_id'] == sid + '-SA01':
            for field, value in zip(('population','outcome','model_or_contrast','result'), ANALYSES[sid].split(';')):
                if value != 'NR':
                    analysis.setdefault(field, value)
        legacy = 'NR means not specified in that retained description' in analysis.get('schema_note', '')
        for field in ('population','outcome','model_or_contrast','result'):
            analysis.setdefault(field, None)
            status = analysis.setdefault('field_status', {})
            extraction = analysis.setdefault('extraction_status', {})
            if analysis[field] is None:
                status[field] = None
                extraction[field] = 'PENDING'
            else:
                status.setdefault(field, 'REPORTED' if analysis[field] != 'NR' else 'NR')
                extraction.setdefault(field, 'RETAINED_DESCRIPTION')
        # Source-read corrections preserve the complete pre-correction record.
        supplement_analysis(analysis, sid)
        for field in ('population','outcome','model_or_contrast','result'):
            if legacy and analysis.get(field) == 'NR':
                analysis.setdefault('migration_previous_values', {})[field] = 'NR'
                analysis[field] = None
                analysis['field_status'][field] = None
                analysis['extraction_status'][field] = 'PENDING'
        if sid not in POPULATIONS:
            if legacy:
                analysis.setdefault('migration_previous_schema_note', analysis.get('schema_note'))
            analysis['schema_note'] = 'Structured fields retain reviewed descriptions; unextracted fields are null/PENDING, not NR. NR requires source-reviewed nonreporting. Original descriptions and evidence remain authoritative.'
    return record

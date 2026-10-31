"""Lossless display projection: raw choices and per-item code keys accompany S2."""
import re
LABELS = {
'Y':'Yes','N':'No','PY':'Probably yes','PN':'Probably no','NI':'No information',
'NR':'Not reported','NA':'Not applicable','UNC':'Unclear (legacy code)',
'UNCLEAR':'Unclear','REPORTED':'Reported','R':'Reported completely','P':'Partially reported',
'R2':'Fully recoverable','R1':'Partly recoverable','R0':'Not recoverable',
'CLS':'Categorical-outcome classification','CONT':'Continuous-outcome estimation',
'CV':'Cross-validation','SPLIT':'Train/test split','BOOT':'Bootstrap','TEMPORAL':'Later-period validation',
'EXTERNAL':'External validation','FIXED05':'Fixed probability of 0.5','YOUDEN':'Youden index',
'VAL_OOF':'Validation or out-of-fold selection','F1':'F1-based selection','CLINICAL':'Clinical criterion',
'USED':'Used','NOT_USED':'Not used','NONE_NR':'None or not reported (unresolved)',
'CURRENT':'Current health state','FUTURE':'Future outcome','MULTI_IMP':'Multiple imputation',
'SINGLE_IMP':'Single imputation','COMPLETE':'Complete-case analysis','OR':'Odds ratio',
'RR':'Risk ratio','HR':'Hazard ratio','PSU':'Primary sampling unit','PSUs':'Primary sampling units',
'AUROC':'Area under ROC curve','AUPRC':'Area under precision–recall curve','DCA':'Decision-curve analysis',
'SHAP':'SHAP','PCA':'Principal component analysis','SVM':'Support vector machine',
}
TOKEN=re.compile(r'\b[A-Z][A-Z0-9_]*\b')
def code_label(code,item=''):
    if code=='R2' and item not in ('OUT16','PRD13'):return 'R-squared'
    return LABELS.get(code,code.replace('_',' ').capitalize())
def response_choices(raw,item=''):
    # Already explicit code=English-label choices use the supplied wording.
    text=re.sub(r'\b[A-Z][A-Z0-9_]*=([^;|]+)',lambda m:m.group(1),raw)
    return TOKEN.sub(lambda m:code_label(m.group(),item),text).replace(' | ','; ')
def lookup_rows(rows):
    return [[r[0],r[4],response_choices(r[4],r[0])] for r in rows if r[4]]

"""Order-invariant reporting existence, never a designation of a primary unit.

Positive > partial (where defined) > unclear > not reported > wholly NA.
Null, empty, absent and unknown tokens are unclear, not evidence of reporting.
Unit-specific mixed responses remain in the lossless public response sheets.
"""
from review_support import POSITIVE_THRESHOLD_CODES
import math


def records(doc, item):
    return doc.get('protocol_items', {}).get(item, [])


def reduce_reporting(rows, positive, partial=(), negative=('NR', 'N', 'NOT_USED')):
    values = [r.get('value') for r in rows]
    def member(v, choices):
        return isinstance(v, (str, int, float)) and v in choices
    if any(member(v, positive) for v in values): return 'Y'
    if any(member(v, partial) for v in values): return 'P'
    if not values or any(not member(v, set(negative) | {'NA'}) for v in values): return 'UNCLEAR'
    if any(member(v, negative) for v in values): return 'NR'
    return 'NA'


def threshold_state(doc):
    return reduce_reporting(records(doc, 'THR01'), POSITIVE_THRESHOLD_CODES)


def threshold_reported(doc):
    return threshold_state(doc) == 'Y'


def linked_independent_units(doc):
    """Require actual evaluation ID, positive THR01 and compatible unit links.

    Matching another evaluation's model/dataset is insufficient. Missing or
    conflicting IDs cannot establish a positive linked indicator.
    """
    units = {}
    for unit in doc.get('units', {}).get('evaluations', []):
        if unit.get('evaluation_id'):
            units.setdefault(unit['evaluation_id'], []).append(unit)
    positives = records(doc, 'THR01')
    matched = set()
    for independent in records(doc, 'THR03'):
        uid = independent.get('unit_id')
        if independent.get('value') != 'USED' or uid not in units: continue
        for threshold in positives:
            if threshold.get('unit_id') != uid or not isinstance(threshold.get('value'), str) or threshold.get('value') not in POSITIVE_THRESHOLD_CODES: continue
            if any(r.get('primary_unit') != 'Evaluation' for r in (threshold, independent)): continue
            links = units[uid] + [threshold.get('related_ids') or {}, independent.get('related_ids') or {}]
            if any(len({r[k] for r in links if r.get(k)}) > 1 for k in ('model_id','outcome_id','dataset_id')): continue
            matched.add(uid)
    return sorted(matched)


def sample_size_reported(doc):
    def valid(v):
        # VAL10 is a participant count, not arbitrary non-missing text.
        if isinstance(v, bool): return False
        try: return math.isfinite(float(v)) and float(v) > 0 and float(v).is_integer()
        except (ValueError, TypeError): return False
    return any(valid(r.get('value')) for r in records(doc, 'VAL10'))


def study_reporting(doc):
    return {'decision_rule': threshold_state(doc),
            'independent_units': linked_independent_units(doc),
            'class_distribution': reduce_reporting(records(doc, 'IMB05'), {'R'}, {'P'}),
            'sample_size': sample_size_reported(doc),
            'original_prevalence': reduce_reporting(records(doc, 'IMB04'), {'ORIGINAL'}, negative=('ALTERED','NR'))}


def reporting_summary(docs):
    from collections import Counter
    by_id = {d['study_id']: study_reporting(d) for d in docs}
    members = {
        'threshold_reported': sorted(s for s,r in by_id.items() if r['decision_rule']=='Y'),
        'threshold_independent': sorted(s for s,r in by_id.items() if r['independent_units']),
        'class_distribution': sorted(s for s,r in by_id.items() if r['class_distribution']=='Y'),
        'sample_size': sorted(s for s,r in by_id.items() if r['sample_size']),
        'original_prevalence': sorted(s for s,r in by_id.items() if r['original_prevalence']=='Y')}
    denominators = {k: sorted(by_id) for k in members}
    denominators['threshold_independent'] = members['threshold_reported']
    return {'policy':'At least one evaluated unit; independence requires the same evaluation ID and compatible links; denominator is threshold-reporting studies.',
            'by_study':by_id,'members':members,'denominators':denominators,
            'decision_states':dict(Counter(r['decision_rule'] for r in by_id.values()))}


def categorical_methods(doc, item):
    """One categorical strategy; multiple distinct observed methods stay MULTIPLE.

    This is not an any-positive reporting indicator or a primary-unit claim.
    Missing/NA states cannot hide a reported method; full mixed records remain.
    """
    vals = {r.get('value') for r in records(doc,item) if isinstance(r.get('value'),str)}
    known = {'PRE01':{'NONE','COMPLETE','SINGLE_IMP','MULTI_IMP','MULTIPLE','MODEL_NATIVE','INDICATOR','OTHER'},
             'IMB01':{'NONE','SMOTE','RANDOM','WEIGHT','ALGO','MULTIPLE','OTHER'}}[item]
    methods = vals & known
    if len(methods)>1 or 'MULTIPLE' in methods: return 'MULTIPLE'
    if methods: return next(iter(methods))
    return reduce_reporting(records(doc,item), set())

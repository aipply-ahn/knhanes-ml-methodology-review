"""Current branch projection of canonical NC05/08/09; never rewrites legacy records.

Callers supply source-supported causal_claim (True/False/None); a task token
alone cannot resolve causal interpretation. Historical assemblers stay unchanged.
"""
def nonclassification_applicability(tasks, causal_claim):
    tasks = set(tasks)
    representation = bool(tasks & {'REPRESENTATION_OR_PATTERN_LEARNING', 'REPRESENTATION'})
    return {'NC05': 'APPLICABLE' if representation or 'IMPUTATION' in tasks else 'NA',
            'NC08': 'APPLICABLE' if causal_claim is True else 'NA' if causal_claim is False else 'UNCLEAR',
            'NC09': 'APPLICABLE' if representation else 'NA'}

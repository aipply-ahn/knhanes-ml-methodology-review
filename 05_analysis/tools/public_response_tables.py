"""Readable final responses plus byte-safe, complete technical preservation.

No locked response is recoded. Array positions are one-based within each item
in this release; source paths retain the zero-based position.
"""
import hashlib
import json
from openpyxl.utils import get_column_letter


def display(value):
    if value is None:
        return '(null)'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, list):
        return '\n'.join(display(v) for v in value) if value else '(empty list)'
    if isinstance(value, dict):
        return '\n'.join(f'{k}: {display(v)}' for k, v in value.items()) if value else '(empty object)'
    return str(value) if value != '' else '(empty string)'


def text_parts(text):
    """Exact concatenation, bounded by characters AND explicit line breaks."""
    part = ''
    for ch in text:
        part += ch
        if len(part) >= 500 or part.count('\n') >= 10:
            yield part
            part = ''
    if part: yield part


RESPONSE_HEADERS = ['study_id', 'item_id', 'primary_unit', 'unit_id', 'response_index',
                    'final_value', 'value_status', 'selected_source', 'related_ids',
                    'evidence_ids', 'rationale', 'item_role', 'json_key',
                    'source_record_path', 'reviewer_id', 'response_status']


def response_rows(doc):
    for item, responses in doc.get('protocol_items', {}).items():
        for i, r in enumerate(responses):
            yield [doc['study_id'], item, display(r.get('primary_unit')), display(r.get('unit_id')),
                   i + 1, display(r.get('value')), display(r.get('value_status')),
                   display(r.get('review_stage')), display(r.get('related_ids')),
                   display(r.get('evidence_ids')), display(r.get('rationale')),
                   display(r.get('item_role')), display(r.get('json_key')),
                   f'protocol_items.{item}[{i}]', display(r.get('reviewer_id')),
                   display(r.get('status'))]


def add_final_response_tables(wb, docs, add_sheet):
    # Full JSON is a technical backup, not a substitute for the reader tables.
    # ensure_ascii also preserves XML-forbidden source characters losslessly.
    continuation = []
    original_add_sheet = add_sheet
    def readable_sheet(wb, name, headers, rows, **kwargs):
        def bounded():
            for row_index, row in enumerate(rows, 2):
                row = list(row)
                for col, value in enumerate(row, 1):
                    full = str(value)
                    if len(full) > 900 or full.count('\n') > 20:
                        ref = f'{name}!{get_column_letter(col)}{row_index}'
                        continuation.extend([row[0], ref, i + 1, part]
                                            for i, part in enumerate(text_parts(full)))
                        row[col-1] = full[:400] + f'\n[Full text: TEXT_CONTINUATIONS; cell_ref={ref}]'
                yield row
        return original_add_sheet(wb, name, headers, bounded(), **kwargs)
    add_sheet = readable_sheet
    add_sheet(wb, 'ITEM_RESPONSES', RESPONSE_HEADERS,
              (r for d in docs for r in response_rows(d)), freeze='F2')
    fields = ['selection_id', 'outcome_id', 'evaluation_ids', 'selected_model_ids',
              'selected_metric_ids', 'criterion', 'tie_status', 'author_designated',
              'evidence_ids', 'rationale']
    add_sheet(wb, 'MODEL_SELECTIONS', ['study_id'] + fields + ['source_record_path'],
              ([d['study_id']] + [display(r.get(k)) for k in fields] + [f'best_model_selections[{i}]']
               for d in docs for i, r in enumerate(d.get('best_model_selections', []))), freeze='C2')
    analysis_fields = []
    for d in docs:
        for i, a in enumerate(d.get('adjudication', {}).get('purpose_evidence_v1_3', {}).get('statistical_analysis_records', [])):
            for field in ('population','outcome','model_or_contrast','result'):
                specific = a.get('field_evidence_ids', {}).get(field)
                analysis_fields.append([d['study_id'], a['statistical_analysis_id'], field,
                    display(a.get(field)), display(a.get('field_status', {}).get(field)),
                    display(a.get('extraction_status', {}).get(field)),
                    display(specific if specific is not None else a.get('evidence_ids')),
                    'Field-specific source' if specific is not None else 'Retained analysis-level evidence; not newly inferred field-specific proof',
                    display(a.get('note')), f'adjudication.purpose_evidence_v1_3.statistical_analysis_records[{i}].{field}'])
    add_sheet(wb, 'ANALYSIS_FIELDS', ['study_id','statistical_analysis_id','field','content','field_status',
              'extraction_status','evidence_ids','evidence_scope','scope_note','source_record_path'], analysis_fields)
    sources, visuals, extra, chunks = [], [], [], []
    covered = {'study_id','protocol_items','best_model_selections','source_package','visual_objects',
               'units','performance_metrics','evidence_registry','adjudication'}
    for d in docs:
        sid = d['study_id']
        for name, r in d.get('source_package', {}).items():
            records = r if isinstance(r, list) else [r]
            for i, record in enumerate(records):
                if not isinstance(record, dict): record = {'value': record}
                for key, val in record.items():
                    sources.append([sid, name, i + 1, key, display(val), f'source_package.{name}'])
        for i, r in enumerate(d.get('visual_objects', [])):
            for key, val in r.items():
                visuals.append([sid, display(r.get('visual_id', r.get('object_id'))), i + 1,
                                key, display(val), f'visual_objects[{i}].{key}'])
        for key, val in d.items():
            if key not in covered:
                extra.append([sid, key, display(val)])
        raw = json.dumps(d, ensure_ascii=True, separators=(',', ':'))
        digest = hashlib.sha256(raw.encode()).hexdigest()
        parts = [raw[i:i+28000] for i in range(0, len(raw), 28000)]
        for i, part in enumerate(parts):
            chunks.append([sid, i + 1, len(parts), digest, part])
    add_sheet(wb, 'SOURCE_PACKAGE', ['study_id','source_group','source_index','field','content','source_record_path'], sources)
    add_sheet(wb, 'VISUAL_DETAILS', ['study_id','visual_id','visual_index','field','content','source_record_path'], visuals)
    add_sheet(wb, 'SOURCE_METADATA', ['study_id','field','content'], extra)
    original_add_sheet(wb, 'SOURCE_JSON', ['study_id','chunk_index','chunk_count','sha256_of_joined_json','json_chunk'], chunks)
    # Long text is split into visible continuation rows, never silently clipped
    # by Excel's 32,767-character cell limit or its 409-point row-height limit.
    for name in ['ITEM_RESPONSES','MODEL_SELECTIONS','ANALYSIS_FIELDS','SOURCE_PACKAGE','VISUAL_DETAILS','SOURCE_METADATA']:
        ws = wb[name]
        for row in ws.iter_rows(min_row=2):
            ws.row_dimensions[row[0].row].height = min(400, max(30, max(
                (len(str(c.value or ''))//40 + str(c.value or '').count('\n') + 1)*12 for c in row)))
    # Existing relational sheets keep their values/JSON untouched. Long reader
    # cells ALSO have a fully readable continuation view keyed by sheet/cell.
    for name in ('RECORD_DETAILS','RECORD_EVIDENCE','EVIDENCE_ANCHORS','README'):
        ws=wb[name]
        for row in ws.iter_rows(min_row=2):
            visible=[c for c in row if not (name=='RECORD_DETAILS' and c.column==14)]
            ws.row_dimensions[row[0].row].height=min(400,max(30,max(
                (len(str(c.value or ''))//38+str(c.value or '').count('\n')+2)*13 for c in visible)))
            if name=='README': continue
            for cell in visible:
                full=str(cell.value or '')
                if len(full)>900 or full.count('\n')>20:
                    continuation.extend([row[0].value,f'{name}!{cell.coordinate}',i+1,part]
                                        for i,part in enumerate(text_parts(full)))
    original_add_sheet(wb, 'TEXT_CONTINUATIONS', ['study_id','cell_ref','part_index','text'], continuation)
    for row in wb['TEXT_CONTINUATIONS'].iter_rows(min_row=2):
        wb['TEXT_CONTINUATIONS'].row_dimensions[row[0].row].height = 360

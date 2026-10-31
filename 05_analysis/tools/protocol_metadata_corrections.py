"""Exact declared current metadata changes; no wildcard exemptions."""
import json
from pathlib import Path
MAP = Path(__file__).resolve().parents[1] / 'prompts/implementation_records/cycle_082/metadata_corrections.json'
def declared_change(item, column, old, new):
    return any(r['item_id']==item and r['column']==column and r['old']==old and r['new']==new
               for r in json.loads(MAP.read_text())['corrections'])

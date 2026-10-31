#!/usr/bin/env python3
"""Create blinded P2 work packets without exposing P1 values or rationales."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P1=ROOT/"data/protocol_v1_2/P1"
OUT=ROOT/"data/protocol_v1_2/P2_blinded"
TEMPLATE=json.loads((ROOT/"KNHANES_ML_study_audit_template_v1.2.json").read_text())
OUT.mkdir(parents=True,exist_ok=True)

for old in OUT.glob("KHM*_P2.json"):
    old.unlink()

for p in sorted(P1.glob("KHM*_P1.json")):
    src=json.loads(p.read_text()); sid=src["study_id"]
    items={}
    for iid, rows in TEMPLATE["protocol_items"].items():
        proto=copy.deepcopy(rows[0])
        proto.update({"unit_id":None,"related_ids":{},"value":None,"value_status":"PENDING",
                      "evidence_ids":[],"reviewer_id":None,"review_stage":"P2",
                      "status":"NOT_STARTED","rationale":None})
        items[iid]=[proto]
    packet={"protocol_version":"1.2","study_id":sid,"canonical_key":src["canonical_key"],
        "file_role":"P2","review_mode":"independent_review","metadata":src["metadata"],
        "source_package":src["source_package"],
        "units":{"reports":[],"datasets":[],"outcomes":[],"models":[],"developments":[],"evaluations":[]},
        "evidence_registry":[],"protocol_items":items,"performance_metrics":[],
        "best_model_selections":[],"visual_objects":[],
        "review_record":{"reviewer_id":None,"review_stage":"P2","review_mode":"independent_review",
                         "date":None,"status":"NOT_STARTED","blind_to_other_reviewer":True},
        "adjudication":{"status":"NOT_APPLICABLE_AT_P2","P1_file":None,"P2_file":f"P2_blinded/{sid}_P2.json",
                        "consensus_entries":[],"unresolved":[],
                        "final_value_rule":"CON > AGREEMENT > UNRESOLVED; P1-only=PROVISIONAL"},
        "blinding":{"P1_values_included":False,"P1_rationales_included":False,"P1_evidence_selection_included":False,
                    "note":"Use the source-package files and protocol instrument only. Do not open P1/final files before locking P2."}}
    (OUT/f"{sid}_P2.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2)+"\n")

readme="""# Protocol v1.2 blinded P2 packets

These 222 files are blank independent-review work packets. They contain bibliographic metadata and source-package paths, but no P1 response, rationale, selected evidence, performance record, or visual interpretation.

The second reviewer must assign a stable reviewer ID, review the source package without opening `P1/` or `final/`, fill all applicable repeated units, and set `review_record.status=COMPLETE`. Only then may `tools/adjudicate_protocol_v1_2.py` compare P1 and P2.

Creating these files does **not** constitute completion of P2.
"""
(OUT/"README.md").write_text(readme)
print({"P2_packets":len(list(OUT.glob('KHM*_P2.json'))),"status":"BLANK_BLINDED_READY"})

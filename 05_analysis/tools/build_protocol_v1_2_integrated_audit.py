#!/usr/bin/env python3
"""Build the integrated study audit directly from adjudicated v1.2 final JSON."""
import csv, json, re
from collections import Counter
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/protocol_v1_2"
DATA = ROOT / "data"
APP = ROOT / "manuscript/internal/supplement_sources"
APP.mkdir(parents=True, exist_ok=True)

def value(record, iid):
    vals = [r.get("value") for r in record["protocol_items"].get(iid, [])]
    if len(vals) == 1: return vals[0]
    return vals

def included(r): return r.get("corpus_status", {}).get("include", value(r, "ELG04") == "Y")
def text(x):
    if isinstance(x, (dict, list)): x=json.dumps(x, ensure_ascii=False, separators=(",", ":"))
    x="" if x is None else str(x)
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", x)
def md(x, limit=900):
    # JSON serialisation represents embedded evidence line breaks as the two
    # characters ``\\n``.  Flatten those before Pandoc sees them; otherwise
    # LaTeX interprets the following word as a control sequence (for example,
    # ``\\nMetrics``).
    s = " ".join(text(x).replace("\\n", " ").replace("|", "/").split())
    return s if len(s) <= limit else s[:limit-4] + " […]"
def write_tsv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        fields=list(dict.fromkeys(k for r in rows for k in r))  # prompt 106: union (new records add source_lines)
        w=csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n", restval=""); w.writeheader(); w.writerows(rows)
def add_sheet(wb, name, rows):
    ws=wb.create_sheet(name); rows=rows or [{"status":"none"}]
    headers=[]
    for row in rows:
        for key in row:
            if key not in headers: headers.append(key)
    ws.append(headers)
    for row in rows: ws.append([text(row.get(h)) for h in headers])
    ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
    for c in ws[1]: c.font=Font(bold=True,color="FFFFFF"); c.fill=PatternFill("solid",fgColor="1F4E78"); c.alignment=Alignment(wrap_text=True,vertical="top")
    for i,h in enumerate(headers,1): ws.column_dimensions[get_column_letter(i)].width=55 if h in {"title","value","rationale","excerpt","interpretation","decision_rationale"} else 18
    for row in ws.iter_rows(min_row=2):
        for c in row: c.alignment=Alignment(wrap_text=True,vertical="top")

records=[json.loads(p.read_text()) for p in sorted((BASE/"final").glob("KHM*_final.json"))]
if len(records)!=255 or any(r.get("adjudication",{}).get("status")!="COMPLETE" for r in records): raise SystemExit("final census incomplete")
kept=[r for r in records if included(r)]

study_rows=[]
for r in kept:
    m=r.get("metadata",{}); vis=r.get("visual_objects",[]); units=r.get("units",{})
    row={"study_id":r["study_id"],"canonical_key":r["canonical_key"],"title":m.get("title"),"year":m.get("publication_year"),
         "authors":m.get("authors"),"journal":m.get("journal"),"doi":m.get("doi"),"include_unique":value(r,"ELG04"),
         "family_id":value(r,"FAM01"),"task":value(r,"TSK01"),"knhanes_role":value(r,"TSK06"),"retraction_status":value(r,"BIB16"),
         "manual_integrity_review":value(r,"ADM09"),"manual_integrity_reason":value(r,"ADM10"),
         "reports_n":len(units.get("reports",[])),"datasets_n":len(units.get("datasets",[])),"outcomes_n":len(units.get("outcomes",[])),
         "models_n":len(units.get("models",[])),"development_n":len(units.get("developments",[])),"evaluation_n":len(units.get("evaluations",[])),
         "metrics_n":len(r.get("performance_metrics",[])),"best_selections_n":len(r.get("best_model_selections",[])),
         "visual_containers_n":sum(v.get("inventory_level")=="CONTAINER" for v in vis),"visual_panels_n":sum(v.get("inventory_level")=="PANEL" for v in vis),
         "evidence_n":len(r.get("evidence_registry",[])),"P1_P2_agreement_items":r["adjudication"]["agreement_items"],
         "adjudicated_items":r["adjudication"]["adjudicated_items"],"corpus_decision":r.get("corpus_status",{}).get("decision","INCLUDE"),
         "classification_reason_codes":r.get("adjudication",{}).get("classification_reason_codes",[]),
         "expanded_model_task_audit":r.get("adjudication",{}).get("expanded_model_task_audit",{}),
         "study_category_and_dataset_use":r.get("adjudication",{}).get("study_category_and_dataset_use",{}),
         "purpose_evidence_v1_3":r.get("adjudication",{}).get("purpose_evidence_v1_3",{}),
         "analytic_flow":r.get("adjudication",{}).get("analytic_flow",{}),
         "decision_rationale":r.get("corpus_status",{}).get("rationale","No corpus-level override; final source-read P2 coding retained.")}
    for iid in ("ELG01","ELG02","OUT02","OUT09","OUT10","POP09","DAT04","PRE02","IMB02","VAL02","VI01","VI02","REP09","REP17","SUR12","SUR14","PD_OVERALL","PE_OVERALL"):
        row[iid]=value(r,iid)
    study_rows.append({k:text(v) for k,v in row.items()})
write_tsv(DATA/"INTEGRATED_STUDY_AUDIT.tsv",study_rows)
(DATA/"INTEGRATED_STUDY_AUDIT.jsonl").write_text(
    "".join(json.dumps(row, ensure_ascii=False, default=str) + "\n" for row in study_rows),
    encoding="utf-8",
)
item_rows=[]; flow_rows=[]; unit_rows=[]; metric_rows=[]; visual_rows=[]; evidence_rows=[]; decision_rows=[]
for r in records:
    sid=r["study_id"]
    for iid,rows in r["protocol_items"].items():
        for x in rows: item_rows.append({"study_id":sid,"included":included(r),"item_id":iid,"primary_unit":x.get("primary_unit"),"unit_id":x.get("unit_id"),"value":x.get("value"),"evidence_ids":x.get("evidence_ids"),"rationale":x.get("rationale"),"reviewer_id":x.get("reviewer_id"),"review_stage":x.get("review_stage")})
    for field_name,x in r.get("adjudication",{}).get("analytic_flow",{}).get("fields",{}).items():
        flow_rows.append({"study_id":sid,"included":included(r),"field":field_name,"value":x.get("value"),
                          "value_status":x.get("value_status"),"source_item_ids":x.get("source_item_ids"),
                          "source_file":x.get("source_file"),"evidence_ids":x.get("evidence_ids"),
                          "derivation_note":x.get("derivation_note")})
    for group,rows in r.get("units",{}).items():
        for x in rows: unit_rows.append({"study_id":sid,"included":included(r),"unit_group":group,"unit":x})
    for x in r.get("performance_metrics",[]): metric_rows.append({"study_id":sid,"included":included(r),**x})
    for x in r.get("visual_objects",[]): visual_rows.append({"study_id":sid,"included":included(r),**x})
    for x in r.get("evidence_registry",[]): evidence_rows.append({"study_id":sid,"included":included(r),**x})
    decision_rows.append({"study_id":sid,"included":included(r),"corpus_status":r.get("corpus_status"),"adjudication":{k:v for k,v in r["adjudication"].items() if k!="disagreements"}})

write_tsv(DATA/"EVIDENCE_LEDGER.tsv", [{k:text(v) for k,v in row.items()} for row in evidence_rows])

wb=Workbook(); wb.remove(wb.active)
summary=json.loads((BASE/"ADJUDICATION_SUMMARY.json").read_text())
add_sheet(wb,"00_README",[{"item":"source","value":"data/protocol_v1_2/final/KHM*_final.json plus adjudication.purpose_evidence_v1_3"},{"item":"status","value":"P1 migration and blinded source-read LLM P2 complete; prespecified rule-based reconciliation complete; v1.3 purpose-and-evidence recoding is post hoc"},{"item":"denominators","value":f"reports=222; included unique={len(kept)}; tasks={dict(Counter(value(r,'TSK01') for r in kept))}"},{"item":"reviewer disclosure","value":"Retained run metadata records model=claude-opus-5 and reviewer_id=P2-CLAUDE-OPUS5; this was an LLM agent, not a second human reviewer. Independent human review of v1.3 is not complete."},{"item":"integrity policy","value":summary["integrity_policy"]},{"item":"retraction policy","value":summary["retraction_policy"]}])
add_sheet(wb,"01_STUDIES",study_rows); add_sheet(wb,"02_ANALYTIC_FLOW",flow_rows); add_sheet(wb,"03_PROTOCOL_ITEMS",item_rows); add_sheet(wb,"04_UNITS",unit_rows)
add_sheet(wb,"05_PERFORMANCE",metric_rows); add_sheet(wb,"06_VISUAL_OBJECTS",visual_rows); add_sheet(wb,"07_EVIDENCE",evidence_rows); add_sheet(wb,"08_DECISIONS",decision_rows)
wb.save(DATA/"INTEGRATED_STUDY_AUDIT.xlsx")

counts=Counter(value(r,"TSK01") for r in kept)
lines=["# Additional file 15. Integrated study-level dataset and evidence ledger","",
 f"This file is generated directly from 222 adjudicated final JSON records. After exclusion of one non-ML report and consolidation of one confirmed preprint–journal pair, the synthesis contains {len(kept)} unique studies: {counts['CLS']} classification, {counts['CONT']} continuous-outcome, and {counts['OTHER']} other-task studies.","",
 "P2 was a blinded LLM source-package review (retained metadata: `model=claude-opus-5`; `reviewer_id=P2-CLAUDE-OPUS5`), not an independent human reviewer. P1–P2 differences were reconciled using a prespecified rule that prioritised the source-read P2 record; named corpus exceptions were recorded separately. Unconfirmed integrity signals were flagged rather than used as automatic exclusions. KHM068 is retained as publication history but excluded from valid performance evidence because it was retracted on 19 August 2026.","",
 "The accompanying XLSX contains a reader-facing analytic-flow sheet linked to the underlying 382 protocol items, analysis units, performance records, visual containers/panels, evidence records, and adjudication decisions. Predictor counts remain separated by analytic stage. `NR` means applicable but not reported/recoverable; `NA` means not applicable.",""]
for n,r in enumerate(kept,1):
    m=r.get("metadata",{}); u=r["units"]; metrics=r.get("performance_metrics",[]); best=r.get("best_model_selections",[]); vis=r.get("visual_objects",[])
    headline=[]
    for s in best[:3]:
        mids=set(s.get("selected_metric_ids") or []); mm=[x for x in metrics if x.get("metric_id") in mids]
        headline.append({"models":s.get("selected_model_ids"),"criterion":s.get("criterion"),"metrics":[{"metric":x.get("metric"),"estimate":x.get("estimate"),"split":x.get("split_label")} for x in mm]})
    lines += [f"## {n}. {r['canonical_key']} ({m.get('publication_year','NR')})","",f"**Title:** {md(m.get('title','NR'))}  ",f"**Study ID / DOI:** {r['study_id']} / {md(m.get('doi') or 'NR')}  ",f"**Task / KNHANES role:** {value(r,'TSK01')} / {value(r,'TSK06')}  ",f"**Post-hoc study-category and dataset-use audit:** {md(r.get('adjudication',{}).get('study_category_and_dataset_use','NA'),1800)}  ",f"**v1.3 purpose–use–output–evidence record:** {md(r.get('adjudication',{}).get('purpose_evidence_v1_3','NA'),2400)}  ",f"**Eligibility / ML boundary:** ELG04={value(r,'ELG04')}; ELG02={value(r,'ELG02')}  ",f"**Analytic flow:** {md(r.get('adjudication',{}).get('analytic_flow',{}),1400)}  ",f"**Selection-restriction dimensions:** {md(r.get('adjudication',{}).get('selection_restriction_dimensions','NA'))}  ",f"**Continuous-study interpretation audit:** {md(r.get('adjudication',{}).get('continuous_interpretation_audit','NA'))}  ",f"**Units:** datasets={len(u['datasets'])}; outcomes={len(u['outcomes'])}; models={len(u['models'])}; developments={len(u['developments'])}; evaluations={len(u['evaluations'])}  ",f"**Best-model record:** {md(headline)}  ",f"**Classification audit reason codes:** {md(r.get('adjudication',{}).get('classification_reason_codes',[]))}  ",f"**Expanded model/task audit:** {md(r.get('adjudication',{}).get('expanded_model_task_audit',{}))}  ",f"**Visual inventory:** containers={sum(v.get('inventory_level')=='CONTAINER' for v in vis)}; panels={sum(v.get('inventory_level')=='PANEL' for v in vis)}; unreadable={sum(v.get('interpretation_status')=='UNREADABLE' for v in vis)}  ",f"**PROBAST+AI:** development={md(value(r,'PD_OVERALL'))}; evaluation={md(value(r,'PE_OVERALL'))}  ",f"**Survey appraisal:** applicability={md(value(r,'SUR12'))}; adherence={md(value(r,'SUR14'))}  ",f"**Integrity/retraction:** ADM09={value(r,'ADM09')}; {md(value(r,'ADM10'))}; BIB16={md(value(r,'BIB16'))}  ",f"**P1–P2:** exact-item agreements={r['adjudication']['agreement_items']}; adjudicated item groups={r['adjudication']['adjudicated_items']}  ",""]
content="\n".join(lines)
(APP/"appendix15_integrated_study_audit.md").write_text(content)
(APP/"appendix8_integrated_study_audit.md").write_text(content.replace("Additional file 15", "Additional file 8",1))
print(json.dumps({"status":"PASS","included":len(kept),"tasks":dict(counts),
 "included_items":sum(x["included"] for x in item_rows),
 "included_metrics":sum(x["included"] for x in metric_rows),
 "included_visuals":sum(x["included"] for x in visual_rows),
 "included_evidence":sum(x["included"] for x in evidence_rows),
 "all_review_packets":{"items":len(item_rows),"metrics":len(metric_rows),"visuals":len(visual_rows),"evidence":len(evidence_rows)}},ensure_ascii=False,indent=2))

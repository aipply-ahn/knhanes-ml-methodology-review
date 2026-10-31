#!/usr/bin/env python3
"""Apply convention-only recodes (no re-reading of sources) to completed P2 answers, then re-assemble.

    python tools/p2_convention_recode.py KHM001 KHM003 ...   # apply + reassemble
    python tools/p2_convention_recode.py --dry-run KHM001    # show planned changes only

Rules (REVIEWER_GUIDE §3, added during the run). Each change keeps the original value in the rationale:
  R1 MOD15/MOD17/MOD18 = NR                          -> NOT_USED   (silent paper: released artefact would be stated)
  R2 SUR04–SUR11 = NOT_USED without evidence_ids      -> NR         (silent paper), unless rationale states explicit non-use
  R3 PRE05 != NA and PRE02 ⊆ {COMPLETE, NONE}         -> NA         (listwise deletion has no fitted step)
  R4 SUR11 != NA and DAT07 == 1                       -> NA         (single survey year)
Judgement-type sweep flags are NOT touched here; they need re-review.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data/protocol_v1_2/P2_work"
EXPLICIT_NON_USE = re.compile(r"unweighted|not\s+(?:be\s+)?(?:use|appl|incorporat|account)|without\s+(?:survey\s+)?weight|did\s+not\s+(?:use|apply|account)|no\s+(?:survey\s+)?weights?\s+(?:were|was)", re.I)


def note(old, rule):
    return f" [Coordinator convention recode {rule}; original P2 value: {json.dumps(old, ensure_ascii=False)}]"


def recode(a):
    changes = []
    items = a.get("items", {})
    def rows(iid):
        r = items.get(iid) or []
        return [r] if isinstance(r, dict) else r
    for iid in ("MOD15", "MOD17", "MOD18"):
        for r in rows(iid):
            if r.get("value") == "NR":
                changes.append((iid, r.get("unit_id"), r["value"], "NOT_USED", "R1"))
                r["rationale"] = ((r.get("rationale") or "Not mentioned in the source package.") + note(r["value"], "R1 silent artefact -> NOT_USED")).strip()
                r["value"] = "NOT_USED"
    for iid in ("SUR04", "SUR05", "SUR06", "SUR07", "SUR08", "SUR09", "SUR10", "SUR11"):
        for r in rows(iid):
            if r.get("value") == "NOT_USED" and not r.get("evidence_ids") and not EXPLICIT_NON_USE.search(r.get("rationale") or ""):
                changes.append((iid, r.get("unit_id"), r["value"], "NR", "R2"))
                r["rationale"] = ((r.get("rationale") or "") + note(r["value"], "R2 silent survey item -> NR")).strip()
                r["value"] = "NR"
    for r in rows("PRE05"):
        allm = next((x.get("value") for x in rows("PRE02") if x.get("unit_id") == r.get("unit_id")), None)
        allm = allm if isinstance(allm, list) else ([allm] if allm else [])
        threshold_drop = re.search(r"missingness\s+threshold|threshold.{0,40}missing|missing.{0,40}threshold|dropp?ed.{0,60}missing", r.get("rationale") or "", re.I)
        if allm and set(allm) <= {"COMPLETE", "NONE"} and r.get("value") != "NA" and not threshold_drop:
            changes.append(("PRE05", r.get("unit_id"), r["value"], "NA", "R3"))
            r["rationale"] = "Listwise deletion only; no fitted missing-data step to nest." + note(r["value"], "R3 complete-case -> NA")
            r["value"] = "NA"; r["evidence_ids"] = []
    # R5 MET_SD -> N when the evaluation has no resampling / repeated evaluation but was coded NA
    #    (item applies to all prediction studies; majority practice is N)
    for r in rows("MET_SD"):
        eid = r.get("unit_id")
        methods = next((x.get("value") for x in rows("VAL02") if x.get("unit_id") == eid), None) or []
        methods = methods if isinstance(methods, list) else [methods]
        reps = next((x.get("value") for x in rows("VAL05") if x.get("unit_id") == eid), None)
        resampled = bool({"CV", "BOOT"} & set(methods)) or (isinstance(reps, int) and reps > 1)
        if eid and not resampled and r.get("value") == "NA":
            changes.append(("MET_SD", eid, r["value"], "N", "R5"))
            r["rationale"] = "No resampling or repeated evaluation; no resampling SD/distribution reported." + note(r["value"], "R5 no resampling, NA -> N")
            r["value"] = "N"; r["evidence_ids"] = []
    # R6 PE_A3 -> NA when no imbalance intervention was used
    imb_vals = [x.get("value") for x in rows("IMB01")]
    if imb_vals and all(v in ("NONE", "NR", "NA") for v in imb_vals):
        for r in rows("PE_A3"):
            if r.get("value") != "NA":
                changes.append(("PE_A3", r.get("unit_id"), r["value"], "NA", "R6"))
                r["rationale"] = "No imbalance adjustment was applied, so evaluation on the unadjusted distribution is not applicable." + note(r["value"], "R6 no imbalance intervention -> NA")
                r["value"] = "NA"; r["evidence_ids"] = []
    dat07 = next((x.get("value") for x in rows("DAT07")), None)
    if dat07 == 1:
        for r in rows("SUR11"):
            if r.get("value") != "NA":
                changes.append(("SUR11", r.get("unit_id"), r["value"], "NA", "R4"))
                r["rationale"] = "Single survey year analysed; combined weights not applicable." + note(r["value"], "R4 single year -> NA")
                r["value"] = "NA"; r["evidence_ids"] = []
    return changes


def main():
    dry = "--dry-run" in sys.argv
    sids = [s for s in sys.argv[1:] if re.fullmatch(r"KHM\d{3}", s)]
    report = []
    for sid in sids:
        p = WORK / "answers" / f"{sid}.json"
        a = json.loads(p.read_text())
        changes = recode(a)
        status = "NO_CHANGE"
        if changes and not dry:
            p.write_text(json.dumps(a, ensure_ascii=False, indent=1) + "\n")
            out = subprocess.run([sys.executable, str(ROOT / "tools/p2_assemble.py"), sid], capture_output=True, text=True, cwd=ROOT)
            status = json.loads(out.stdout.strip().splitlines()[-1])["status"] if out.stdout.strip() else "ASSEMBLER_ERROR"
        elif changes:
            status = "PLANNED"
        report.append({"study_id": sid, "status": status, "changes": [dict(zip(("item", "unit", "from", "to", "rule"), c)) for c in changes]})
        print(json.dumps({"study_id": sid, "status": status, "n_changes": len(changes),
                          "rules": sorted({c[4] for c in changes})}, ensure_ascii=False))
    log = WORK / "CONVENTION_RECODE_LOG.json"
    prev = json.loads(log.read_text()) if log.exists() else []
    if not dry:
        log.write_text(json.dumps(prev + report, ensure_ascii=False, indent=1) + "\n")


if __name__ == "__main__":
    main()

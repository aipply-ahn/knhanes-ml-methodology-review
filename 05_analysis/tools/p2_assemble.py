#!/usr/bin/env python3
"""Assemble and validate a blinded P2 record from a reviewer answer file.

    python tools/p2_assemble.py KHM001            # validate + write P2_blinded/KHM001_P2.json if PASS
    python tools/p2_assemble.py KHM001 --dry-run  # validate only
    python tools/p2_assemble.py --summary         # P2_work/P2_VALIDATION.json over all answer files

Inputs (never P1/, final/, final_consensus/, data/INTEGRATED_STUDY_AUDIT.tsv or results/):
  data/protocol_v1_2/P2_work/answers/KHM001.json   reviewer answers (see P2_work/REVIEWER_GUIDE.md)
  data/protocol_v1_2/P2_blinded/KHM001_P2.json      blank packet (metadata, source package)
  data/protocol_v1_2/P2_work/ITEM_SPEC.json         parsed protocol instrument

system_metadata / derived / automated_validation items and the OBJ*/SUP03-04 projections are
computed here from the P2 record itself, so the reviewer enters each fact once.
"""
import datetime, hashlib, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/protocol_v1_2"
WORK = BASE / "P2_work"
SPEC = json.loads((WORK / "ITEM_SPEC.json").read_text())
REVIEWER_ID = "P2-CLAUDE-OPUS5"
# review loop 20261024: --answers-dir answers_A|answers_B validates an independent extraction (always with --dry-run)
ANSWERS_DIR = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--answers-dir=")), "answers")
ALLOWED_SOURCE_PREFIXES = ("references/pdf/", "references/md/", "references/supplements/",
                           "references/supplements_text/")
FORBIDDEN = ("data/protocol_v1_2/P1", "data/protocol_v1_2/final", "INTEGRATED_STUDY_AUDIT", "results/")
METRIC_ITEMS = {"ACC": "MET_ACC_R", "BACC": "MET_BACC_R", "AUROC": "MET_AUROC_R", "AUPRC": "MET_AUPRC_R",
                "SENS": "MET_SENS_R", "SPEC": "MET_SPEC_R", "PPV": "MET_PPV_R", "NPV": "MET_NPV_R",
                "F1": "MET_F1_R", "MCC": "MET_MCC_R", "KAPPA": "MET_KAPPA_R", "BRIER": "MET_BRIER_R",
                "LOGLOSS": "MET_LOGLOSS_R", "CALSLOPE": "MET_CALSLOPE_R", "CALINT": "MET_CALINT_R",
                "CALPLOT": "MET_CALPLOT_R", "DCA": "MET_DCA_R", "RMSE": "MET_RMSE_R", "MSE": "MET_MSE_R",
                "MAE": "MET_MAE_R", "R2": "MET_R2_R"}
REGRESSION_METRICS = {"RMSE", "MSE", "MAE", "R2"}
METRIC_CODES = set(METRIC_ITEMS) | {"OTHER"}
UNIT_GROUP = {"Report": "reports", "Dataset": "datasets", "Outcome": "outcomes", "Model": "models",
              "Development": "developments", "Evaluation": "evaluations"}
UNIT_KEY = {"reports": "report_id", "datasets": "dataset_id", "outcomes": "outcome_id", "models": "model_id",
            "developments": "development_id", "evaluations": "evaluation_id"}
UNIT_PATTERN = {"reports": r"-R\d{2}", "datasets": r"-DS\d{2}", "outcomes": r"-O\d{2}", "models": r"-M\d{2}",
                "developments": r"-D\d{2}", "evaluations": r"-E\d{2}"}
REVIEWER_ROLES = ("reviewer_entered", "appraisal_judgement")
# values that assert absence/non-applicability and therefore need no quotable evidence
NO_EVIDENCE_VALUES = {"NA", "NR", "ABSENT", "N", "NI", "NONE", "NONE_NR", "NAU", "CU", "UNC", "NOT_USED", "PENDING", "R0"}
# reviewer items projected from visual_objects[] / source_package (entered once, not twice)
OBJ_FIELDS = {"OBJ02": "object_type", "OBJ03": "object_label", "OBJ04": "panel_label", "OBJ05": "pdf_page",
              "OBJ05B": "printed_page", "OBJ06": "caption_start_anchor", "OBJ06B": "caption_end_anchor",
              "OBJ07": "interpretation_status", "OBJ08": "metric_sensitive", "OBJ09": "extracted_values",
              "OBJ10": "original_resolution_retry", "OBJ11": "visual_discrepancy_adjudication"}
PROJECTED = set(OBJ_FIELDS) | {"SUP03", "SUP04"}


def norm_text(s):
    # PDF text layers of some journals encode '=' as '¼' and '+' as 'þ'; drop them before NFKC ('¼' -> '14')
    s = str(s).replace("¼", "").replace("þ", "")
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[^0-9a-z가-힣]+", "", s)


class Ctx:
    def __init__(self, sid):
        self.sid = sid
        self.errors, self.warnings = [], []
        self.packet = json.loads((BASE / "P2_blinded" / f"{sid}_P2.json").read_text())
        self.ans = json.loads((WORK / ANSWERS_DIR / f"{sid}.json").read_text())
        self.key = self.packet["canonical_key"]

    def err(self, m): self.errors.append(m)
    def warn(self, m): self.warnings.append(m)


def source_corpus(ctx):
    """Normalised text of the source package for excerpt verification (cached)."""
    cache = WORK / "text_cache" / f"{ctx.sid}.txt"
    if cache.exists():
        return cache.read_text()
    parts = []
    for fl in ctx.packet["source_package"]["main_text"]["files"]:
        p = ROOT / fl["path"]
        if p.suffix == ".md":
            parts.append(p.read_text(encoding="utf-8", errors="ignore"))
        elif p.suffix == ".pdf":
            import fitz
            with fitz.open(p) as doc:
                parts.extend(page.get_text() for page in doc)
            # PyMuPDF drops columns/pages in some layouts; add pdftotext output as a second text layer
            import subprocess
            try:
                parts.append(subprocess.run(["pdftotext", "-enc", "UTF-8", str(p), "-"],
                                            capture_output=True, text=True, timeout=120).stdout)
            except Exception:
                pass
    st = ROOT / "references/supplements_text"
    if (st / f"{ctx.key}.md").exists():
        parts.append((st / f"{ctx.key}.md").read_text(encoding="utf-8", errors="ignore"))
    if (st / ctx.key).is_dir():
        for f in sorted((st / ctx.key).rglob("*")):
            if f.is_file() and f.suffix.lower() in (".txt", ".md", ".csv", ".tsv"):
                parts.append(f.read_text(encoding="utf-8", errors="ignore"))
    for s in ctx.packet["source_package"]["supplement_files"]:
        for fl in s.get("files", []):
            p = ROOT / (fl if isinstance(fl, str) else fl["path"])
            if p.suffix.lower() == ".pdf" and p.exists():
                import fitz
                with fitz.open(p) as doc:
                    parts.extend(page.get_text() for page in doc)
    text = norm_text("\n".join(parts))
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text)
    return text


def build_units(ctx):
    units = {g: [] for g in UNIT_KEY}
    for g, rows in (ctx.ans.get("units") or {}).items():
        if g not in units:
            ctx.err(f"units: unknown group {g}"); continue
        for u in rows:
            uid = u.get(UNIT_KEY[g])
            if not isinstance(uid, str) or not re.fullmatch(re.escape(ctx.sid) + UNIT_PATTERN[g], uid):
                ctx.err(f"units.{g}: bad id {uid!r}")
            units[g].append(u)
    if not units["reports"]:
        units["reports"] = [{"report_id": f"{ctx.sid}-R01", "canonical_key": ctx.key}]
    ids = {g: {u[UNIT_KEY[g]] for u in rows} for g, rows in units.items()}
    for g in ("developments", "evaluations"):
        for u in units[g]:
            for k, grp in (("model_id", "models"), ("outcome_id", "outcomes"), ("dataset_id", "datasets")):
                if u.get(k) not in ids[grp]:
                    ctx.err(f"units.{g}/{u.get(UNIT_KEY[g])}: {k}={u.get(k)!r} not a defined unit")
    return units, ids


def check_evidence(ctx):
    reg = ctx.ans.get("evidence_registry") or []
    corpus = source_corpus(ctx)
    evid, unmatched = set(), 0
    for e in reg:
        eid = e.get("evidence_id")
        if not isinstance(eid, str) or not re.fullmatch(re.escape(ctx.sid) + r"-EV\d{3,4}", eid):
            ctx.err(f"evidence: bad id {eid!r}")
        if eid in evid:
            ctx.err(f"evidence: duplicate {eid}")
        evid.add(eid)
        src = str(e.get("source_file") or "")
        if any(f in src for f in FORBIDDEN) or not src.startswith(ALLOWED_SOURCE_PREFIXES):
            ctx.err(f"evidence {eid}: source_file outside blinded source package: {src!r}")
        elif not (ROOT / src).exists():
            ctx.err(f"evidence {eid}: source_file does not exist: {src!r}")
        exc = e.get("excerpt")
        if not exc:
            ctx.err(f"evidence {eid}: empty excerpt")
            continue
        e.setdefault("interpretation_status", "NATIVE")
        if e["interpretation_status"] != "NATIVE" and not (e.get("pdf_page") or e.get("object_label")):
            # image-read evidence cannot be text-matched; require it to be traceable to a page/object
            ctx.warn(f"evidence {eid}: {e['interpretation_status']} (image-read) evidence has no pdf_page or object_label")
        if e["interpretation_status"] == "NATIVE":
            n = norm_text(exc)
            # allow ellipsis-joined excerpts: every fragment of >=12 normalised chars must be found
            frags = [norm_text(x) for x in re.split(r"\.\.\.|…|\[\.\.\.\]", exc)]
            frags = [f for f in frags if len(f) >= 12] or [n]
            if not all(f in corpus for f in frags):
                unmatched += 1
                ctx.warn(f"evidence {eid}: NATIVE excerpt not found verbatim in source text")
    if reg and unmatched / len(reg) > 0.10:
        ctx.err(f"evidence: {unmatched}/{len(reg)} NATIVE excerpts not found in source text (>10%)")
    for e in reg:
        for k in ("section", "subsection", "pdf_page", "printed_page", "object_label", "panel_label",
                  "table_row", "table_column", "start_anchor", "end_anchor", "source_type"):
            e.setdefault(k, None)
    return reg, evid


def stamp(x, why):
    x.setdefault("reviewer_id", REVIEWER_ID); x["reviewer_id"] = REVIEWER_ID
    x["review_stage"] = "P2"; x["status"] = "COMPLETE"
    x.setdefault("rationale", None); x.setdefault("evidence_ids", [])
    return x


def check_value(ctx, iid, spec, v, where):
    fmt, codes = spec["format"], spec["codes"]
    if v is None:
        ctx.err(f"{where}: null value"); return
    if v == "NA" and spec.get("applicability") not in ("All", "Included"):
        return  # conditional item whose condition is not met; cond() checks consistency
    special = {"NA", "NR", "UNC"}
    if fmt == "Single choice":
        if v not in codes:
            ctx.err(f"{where}: {v!r} not in {codes}")
    elif fmt.startswith("Multiple choice"):
        vals = v if isinstance(v, list) else None
        if vals is None or not vals:
            ctx.err(f"{where}: multiple choice must be a non-empty JSON array, got {v!r}")
        elif not set(vals) <= set(codes):
            ctx.err(f"{where}: {sorted(set(vals) - set(codes))} not in {codes}")
    elif fmt == "Integer":
        if not (isinstance(v, int) and not isinstance(v, bool)) and v not in special:
            ctx.err(f"{where}: integer expected, got {v!r}")
    elif fmt == "Decimal":
        if not isinstance(v, (int, float)) and v not in special:
            ctx.err(f"{where}: number expected, got {v!r}")
    elif fmt == "Integer array":
        if not (isinstance(v, list) and all(isinstance(i, int) for i in v)) and v not in special:
            ctx.err(f"{where}: integer array expected, got {v!r}")
    elif fmt in ("Text", "Long text", "Identifier", "Date"):
        if not isinstance(v, str) or not v.strip():
            ctx.err(f"{where}: non-empty string expected, got {v!r}")


def first(items, iid):
    rows = items.get(iid) or []
    return rows[0]["value"] if rows else None


def main_one(sid, dry):
    ctx = Ctx(sid)
    units, ids = build_units(ctx)
    reg, evid = check_evidence(ctx)
    ans_items = ctx.ans.get("items") or {}
    today = ctx.ans.get("review_date") or datetime.date.today().isoformat()
    sp = ctx.packet["source_package"]
    report_id = units["reports"][0]["report_id"]
    items = {}

    def row(iid, value, unit_id, related=None, evidence=None, rationale=None):
        s = SPEC[iid]
        return {"item_role": s["item_role"], "primary_unit": s["primary_unit"], "unit_id": unit_id,
                "related_ids": related or {}, "json_key": s["json_key"], "value": value,
                "value_status": "ANSWERED", "evidence_ids": evidence or [], "reviewer_id": REVIEWER_ID,
                "review_stage": "P2", "status": "COMPLETE", "rationale": rationale}

    def related_for(g, uid):
        if g in ("developments", "evaluations"):
            u = next(x for x in units[g] if x[UNIT_KEY[g]] == uid)
            return {k: u[k] for k in ("model_id", "outcome_id", "dataset_id")}
        return {"report_id": report_id} if g == "reports" else {}

    # ---- reviewer-entered items ------------------------------------------------------------
    for iid, spec in SPEC.items():
        if spec["item_role"] not in REVIEWER_ROLES or iid in PROJECTED:
            continue
        given = ans_items.get(iid)
        if given is None:
            ctx.err(f"{iid}: missing reviewer answer"); continue
        if isinstance(given, dict):
            given = [given]
        g = UNIT_GROUP.get(spec["primary_unit"])
        expected = sorted(ids[g]) if g else [sid]
        if g == "models":
            # model-level items are required for FINAL models; CANDIDATE/BASELINE rows are optional
            final = sorted(u["model_id"] for u in units["models"] if u.get("role") == "FINAL")
            expected = final or expected
        out = []
        for j, a in enumerate(given):
            uid = a.get("unit_id") or (sid if not g else None)
            where = f"{iid}[{uid}]"
            if g:
                if not expected:
                    if a.get("value") != "NA":
                        ctx.err(f"{where}: no {g} units defined, so the only allowed row is value NA")
                elif uid not in ids[g]:
                    ctx.err(f"{where}: unit_id must be one of {expected}")
            v = a.get("value")
            check_value(ctx, iid, spec, v, where)
            ev = a.get("evidence_ids") or []
            bad = set(ev) - evid
            if bad:
                ctx.err(f"{where}: unknown evidence {sorted(bad)}")
            vals = v if isinstance(v, list) else [v]
            substantive = not all(isinstance(x, str) and x in NO_EVIDENCE_VALUES for x in vals)
            if substantive and not ev and iid != "ADM07":  # ADM07 = reviewer certainty, not a source fact
                ctx.err(f"{where}: substantive value without evidence_ids")
            rat = a.get("rationale")
            # long-text Judgement items carry their reasoning in the value itself
            needs_rat = ((spec["item_role"] == "appraisal_judgement" or spec["nature"] == "Judgement")
                         and v != "NA" and spec["format"] != "Long text")
            if (needs_rat or "OTHER" in vals or "UNC" in vals) and not (isinstance(rat, str) and rat.strip()):
                ctx.err(f"{where}: rationale required")
            rel = related_for(g, uid) if g and uid in ids.get(g, ()) else {}
            rel.update(a.get("related_ids") or {})
            out.append(row(iid, v, uid, rel, ev, rat))
        if g and expected:
            got = [r["unit_id"] for r in out]
            if len(got) != len(set(got)) or not set(expected) <= set(got) or not set(got) <= ids[g]:
                ctx.err(f"{iid}: rows {sorted(str(u) for u in got)} must cover units {expected} once each")
        items[iid] = out

    task = first(items, "TSK01")

    # ---- protocol conditional rules (NA consistency) -----------------------------------------
    def cond(iid, applicable, label):
        for r in items.get(iid, []):
            if not applicable and r["value"] != "NA":
                ctx.err(f"{iid}[{r['unit_id']}]: must be NA when not ({label})")
            if applicable and r["value"] == "NA" and SPEC[iid]["item_role"] in REVIEWER_ROLES:
                ctx.warn(f"{iid}[{r['unit_id']}]: NA although applicable ({label})")
    if items:
        cond("TSK08", first(items, "TSK07") == "Y", "TSK07=Y")
        cond("TSK11", task == "OTHER", "TSK01=OTHER")
        cond("NC10", task == "OTHER", "TSK01=OTHER")
        for i in ("NC01", "NC02", "NC03"):
            cond(i, task == "CONT", "TSK01=CONT")
        sub = first(items, "TSK11") or []
        sub = sub if isinstance(sub, list) else []
        cond("NC04", "IMPUTATION" in sub, "TSK11 contains IMPUTATION")
        cond("NC05", bool({"IMPUTATION", "REPRESENTATION"} & set(sub)), "TSK11 IMPUTATION/REPRESENTATION")
        cond("NC06", "CLUSTERING" in sub, "TSK11 contains CLUSTERING"); cond("NC07", "CLUSTERING" in sub, "CLUSTERING")
        cond("NC08", "CAUSAL" in sub, "TSK11 contains CAUSAL"); cond("NC09", "REPRESENTATION" in sub, "REPRESENTATION")
        cond("ELG05", first(items, "ELG04") == "N", "ELG04=N")
        cond("POP17", first(items, "POP16") == "Y", "POP16=Y")
        cond("DAT16", first(items, "DAT15") == "Y", "DAT15=Y"); cond("DAT17", first(items, "DAT15") == "Y", "DAT15=Y")
        for i in [f"REP{n:02d}" for n in range(1, 20)]:
            cond(i, task in ("CLS", "CONT"), "D_PROB")
        rat = {i: first(items, i) for i in ("RAT_PERF", "RAT_SCREEN", "RAT_COMPLEX", "RAT_FACTOR", "RAT_METHOD", "RAT_DEPLOY")}
        if "PRESENT" in rat.values() and first(items, "RAT_NONE") != "ABSENT":
            ctx.err("RAT_NONE must be ABSENT when another RAT_* is PRESENT")
        if rat and all(v == "ABSENT" for v in rat.values()) and first(items, "RAT_NONE") != "PRESENT":
            ctx.err("RAT_NONE must be PRESENT when all other RAT_* are ABSENT")
        for r in items.get("VI01", []):
            used = r["value"] == "USED"
            for i in ["VI02", "VI03", "VI04", "VI05", "VI06", "VI08", "VI10", "VI11", "VI16", "VI17", "VI18"]:
                for rr in items.get(i, []):
                    if rr["unit_id"] == r["unit_id"] and not used and rr["value"] != "NA":
                        ctx.err(f"{i}[{rr['unit_id']}]: must be NA when VI01 != USED")
        for r in items.get("VI11", []):
            for i in ["VI12", "VI13", "VI14", "VI15"]:
                for rr in items.get(i, []):
                    if rr["unit_id"] == r["unit_id"] and r["value"] != "USED" and rr["value"] != "NA":
                        ctx.err(f"{i}[{rr['unit_id']}]: must be NA when VI11 != USED")

    # ---- performance metrics / selections / visual objects ----------------------------------
    metrics = [stamp(m, "metric") for m in (ctx.ans.get("performance_metrics") or [])]
    metric_ids = set()
    for m in metrics:
        mid = m.get("metric_id")
        if not isinstance(mid, str) or not re.fullmatch(re.escape(sid) + r"-PM\d{3,4}", mid) or mid in metric_ids:
            ctx.err(f"performance_metrics: bad/duplicate id {mid!r}")
        metric_ids.add(mid)
        if m.get("metric") not in METRIC_CODES:
            ctx.err(f"{mid}: metric {m.get('metric')!r} not in {sorted(METRIC_CODES)}")
        if m.get("metric") == "OTHER" and not m.get("reported_text"):
            ctx.err(f"{mid}: OTHER metric needs reported_text")
        ev = m.get("evaluation_id")
        if ev not in ids["evaluations"]:
            ctx.err(f"{mid}: evaluation_id {ev!r} undefined")
        else:
            u = next(x for x in units["evaluations"] if x["evaluation_id"] == ev)
            for k in ("model_id", "outcome_id", "dataset_id"):
                m.setdefault(k, u[k])
                if m[k] != u[k] and k != "model_id":
                    ctx.err(f"{mid}: {k} {m[k]} disagrees with evaluation {ev}")
        if not m.get("evidence_ids") or set(m["evidence_ids"]) - evid:
            ctx.err(f"{mid}: evidence_ids missing/unknown")
        if m.get("estimate") is None and m.get("metric") not in ("CALPLOT", "DCA"):
            # allowed only for impossible printed values kept verbatim in reported_text
            if not (m.get("reported_text") or "").strip():
                ctx.err(f"{mid}: estimate is null (keep the printed value in reported_text if it was nulled as impossible)")
        for k in ("lower_ci", "upper_ci", "sd", "class_label", "threshold", "split_label", "summary_type",
                  "reported_text"):
            m.setdefault(k, None)
        m.setdefault("author_designated_best", False)

    selections = [stamp(s, "sel") for s in (ctx.ans.get("best_model_selections") or [])]
    for s in selections:
        sel = s.get("selection_id")
        if s.get("outcome_id") not in ids["outcomes"]:
            ctx.err(f"{sel}: outcome_id undefined")
        if set(s.get("selected_model_ids") or []) - ids["models"]:
            ctx.err(f"{sel}: selected_model_ids undefined")
        if set(s.get("selected_metric_ids") or []) - metric_ids:
            ctx.err(f"{sel}: selected_metric_ids undefined")
        if set(s.get("evaluation_ids") or []) - ids["evaluations"]:
            ctx.err(f"{sel}: evaluation_ids undefined")
        if set(s.get("evidence_ids") or []) - evid:
            ctx.err(f"{sel}: unknown evidence")
        if s.get("tie_status") not in ("NO_TIE", "TIE", "TIE_AT_REPORTED_PRECISION", "POSSIBLE_TIE", "NA"):
            ctx.err(f"{sel}: tie_status {s.get('tie_status')!r} not in NO_TIE/TIE/TIE_AT_REPORTED_PRECISION/POSSIBLE_TIE/NA")

    visuals = [stamp(v, "vis") for v in (ctx.ans.get("visual_objects") or [])]
    vids = {v.get("object_id") for v in visuals}
    for v in visuals:
        oid = v.get("object_id")
        if not isinstance(oid, str) or not re.fullmatch(re.escape(sid) + r"-V\d{4}", oid):
            ctx.err(f"visual: bad id {oid!r}")
        check_value(ctx, "OBJ02", SPEC["OBJ02"], v.get("object_type"), f"{oid}.object_type")
        check_value(ctx, "OBJ07", SPEC["OBJ07"], v.get("interpretation_status"), f"{oid}.interpretation_status")
        if v.get("inventory_level") not in ("CONTAINER", "PANEL"):
            ctx.err(f"{oid}: inventory_level must be CONTAINER or PANEL")
        if v.get("inventory_level") == "PANEL" and v.get("parent_object_id") not in vids:
            ctx.err(f"{oid}: panel without valid parent_object_id")
        if v.get("source_scope") not in ("MAIN", "SUPPLEMENT"):
            ctx.err(f"{oid}: source_scope must be MAIN or SUPPLEMENT")
        if not isinstance(v.get("pdf_page"), int) and v.get("source_scope") == "MAIN":
            ctx.err(f"{oid}: pdf_page integer required for MAIN objects")
        for k, code_item in (("metric_sensitive", "OBJ08"), ("original_resolution_retry", "OBJ10")):
            v.setdefault(k, "NA")
            check_value(ctx, code_item, SPEC[code_item], v[k], f"{oid}.{k}")
        v.setdefault("visual_discrepancy_adjudication", "NA")
        v.setdefault("extracted_values", [])
        if set(v.get("evidence_ids") or []) - evid:
            ctx.err(f"{oid}: unknown evidence")
        for k in ("panel_label", "printed_page", "visible_text", "interpretation", "caption_end_anchor",
                  "caption_start_anchor", "source_file"):
            v.setdefault(k, None)
        v.setdefault("vision_required", v.get("interpretation_status") in ("COMPLETE", "UNCERTAIN", "UNREADABLE"))

    # ---- system_metadata / derived / automated / projected items ---------------------------
    meta = ctx.packet["metadata"]
    md_front = {}
    mdp = next((ROOT / f["path"] for f in sp["main_text"]["files"] if f["type"] == "extracted_markdown"), None)
    if mdp and mdp.exists():
        head = mdp.read_text(encoding="utf-8", errors="ignore").split("---")[1] if mdp.read_text(encoding="utf-8", errors="ignore").startswith("---") else ""
        for line in head.splitlines():
            if ":" in line:
                k, v = line.split(":", 1); md_front[k.strip()] = v.strip().strip('"')
    pdfp = next((ROOT / f["path"] for f in sp["main_text"]["files"] if f["type"] == "main_pdf"), None)
    pages = "NR"
    if pdfp and pdfp.exists():
        import fitz
        with fitz.open(pdfp) as doc:
            pages = doc.page_count
    sysvals = ctx.ans.get("system_metadata") or {}

    def nz(x):
        return x if x not in (None, "", [], "None") else "NR"
    authors = meta.get("authors") or []
    author_str = "; ".join(a if isinstance(a, str) else a.get("name", str(a)) for a in authors)
    study_level = {
        "ADM01": sid, "ADM03": sid, "ADM04": "P2", "ADM05": REVIEWER_ID, "ADM06": today,
        "ADM08": sp["main_text"].get("sha256") or "NR",
        "FAM01": sysvals.get("FAM01", "NA"), "FAM02": len(units["reports"]),
        "SUP01": sum(len(s.get("files", [])) for s in sp["supplement_files"]),
        "SUP02": [{"supplement_id": s.get("supplement_id"), "availability": s.get("availability"),
                   "review_status": s.get("review_status")} for s in sp["supplement_files"]] or "NA",
        "TSK09": "Y" if task == "CLS" else "N",
        "TSK10": "Y" if task in ("CLS", "CONT") else "N",
    }
    for iid in ("ADM09", "ADM10"):
        study_level[iid] = sysvals.get(iid)
    if study_level["ADM09"] not in ("Y", "N", "UNC", "NA"):
        ctx.err("system_metadata.ADM09 (manual_followup) must be Y/N/UNC/NA")
    if study_level["ADM09"] == "Y" and not sysvals.get("ADM10"):
        ctx.err("system_metadata.ADM10 required when ADM09=Y")
    study_level["ADM10"] = sysvals.get("ADM10") if study_level["ADM09"] == "Y" else "NA"
    years_n = first(items, "DAT07")
    years = first(items, "DAT04")
    if isinstance(years_n, int) and years_n > 1 and isinstance(years, list) and years:
        ys = sorted(set(years))
        study_level["DAT09"] = "Y" if ys[-1] - ys[0] + 1 != len(ys) else "N"
    else:
        study_level["DAT09"] = "NA"
    for iid, v in study_level.items():
        items[iid] = [row(iid, v, sid)]
    bib = {"BIB01": meta.get("title"), "BIB02": authors[0] if authors and isinstance(authors[0], str) else nz(author_str.split(";")[0]),
           "BIB03": nz(author_str), "BIB04": nz(meta.get("journal") or md_front.get("journal")),
           "BIB05": meta.get("publication_year") or "NR", "BIB06": "NR", "BIB07": "NR", "BIB08": nz(meta.get("language")),
           "BIB09": nz(meta.get("doi")), "BIB10": nz(md_front.get("pmid")), "BIB11": "NR", "BIB12": "NR",
           "BIB13": nz(f"https://doi.org/{meta['doi']}" if meta.get("doi") else None),
           "BIB14": sp["main_text"]["files"][0]["path"] if sp["main_text"]["files"] else "NR",
           "BIB15": pages, "BIB16": "NR"}
    bib.update({k: v for k, v in sysvals.items() if k.startswith("BIB")})
    items["ADM02"] = [row("ADM02", u["report_id"], u["report_id"], {"study_id": sid}) for u in units["reports"]]
    for iid, v in bib.items():
        items[iid] = [row(iid, v, report_id, {"study_id": sid})]
    for iid, g in (("DAT00", "datasets"), ("OUT01", "outcomes"), ("MOD01", "models"), ("VAL01", "evaluations")):
        items[iid] = [row(iid, u[UNIT_KEY[g]], u[UNIT_KEY[g]], related_for(g, u[UNIT_KEY[g]])) for u in units[g]] \
            or [row(iid, "NA", None)]

    # MET_*_R per evaluation from performance_metrics[]
    outcome_scale = {r["unit_id"]: r["value"] for r in items.get("OUT09", [])}
    for code, iid in METRIC_ITEMS.items():
        rows = []
        for u in units["evaluations"]:
            eid = u["evaluation_id"]
            reported = any(m.get("evaluation_id") == eid and m.get("metric") == code for m in metrics)
            cont = outcome_scale.get(u["outcome_id"]) == "CONTINUOUS"
            applicable = cont if code in REGRESSION_METRICS else (not cont or code in ("CALSLOPE", "CALINT", "CALPLOT"))
            val = "R" if reported else ("NR" if applicable else "NA")
            rows.append(row(iid, val, eid, related_for("evaluations", eid)))
        items[iid] = rows or [row(iid, "NA", None)]

    # BEST01-03 per outcome from best_model_selections[]
    for iid in ("BEST01", "BEST02", "BEST03"):
        rows = []
        for u in units["outcomes"]:
            oid = u["outcome_id"]
            sels = [s for s in selections if s.get("outcome_id") == oid]
            if task not in ("CLS", "CONT"):
                val = "NA"
            elif iid == "BEST01":
                val = "Y" if any(s.get("criterion") for s in sels) else "N"
            elif not sels:
                val = "NA"
            elif iid == "BEST02":
                val = "Y" if all(s.get("selected_model_ids") and s.get("selected_metric_ids") for s in sels) else "N"
            else:
                val = "Y" if all(s.get("evaluation_ids") and s.get("evidence_ids") and s.get("rationale") for s in sels) else "N"
            rows.append(row(iid, val, sid, {"outcome_id": oid}))
        items[iid] = rows or [row(iid, "NA", sid)]

    # MED01-15 from visual_objects[]
    def count(scope, pred):
        return sum(1 for v in visuals if v.get("source_scope") == scope and pred(v))
    fig_types = ("FIGURE", "FLOW", "GRAPH_ABS")
    def fig_container(v): return v["inventory_level"] == "CONTAINER" and v.get("object_type") in fig_types
    def unpanelled(v): return fig_container(v) and not any(c.get("parent_object_id") == v["object_id"] for c in visuals)
    med = {}
    for scope, (a, b, c, d, e) in (("MAIN", ("MED01", "MED02", "MED03", "MED04", "MED05")),
                                   ("SUPPLEMENT", ("MED06", "MED07", "MED08", "MED09", "MED10"))):
        med[a] = count(scope, fig_container)
        med[b] = count(scope, lambda v: v.get("object_type") == "FIG_PANEL")
        med[c] = count(scope, unpanelled)
        med[d] = count(scope, lambda v: v["inventory_level"] == "CONTAINER" and v.get("object_type") == "TABLE")
        med[e] = count(scope, lambda v: v.get("object_type") == "TABLE_PANEL")
    med["MED11"] = sum(1 for v in visuals if v.get("vision_required"))
    med["MED12"] = sum(1 for v in visuals if v.get("interpretation_status") == "COMPLETE")
    med["MED13"] = sum(1 for v in visuals if v.get("interpretation_status") == "UNCERTAIN")
    med["MED14"] = sum(1 for v in visuals if v.get("interpretation_status") == "UNREADABLE")
    med["MED15"] = sum(1 for v in visuals if v.get("metric_sensitive") == "Y")
    for iid, v in med.items():
        items[iid] = [row(iid, v, sid)]

    # OBJ01-11 projected from visual_objects[]
    for iid in ["OBJ01", "OBJ03B"] + list(OBJ_FIELDS):
        rows = []
        for v in visuals:
            rel = {"report_id": report_id}
            if v.get("parent_object_id"):
                rel["parent_object_id"] = v["parent_object_id"]
            if iid == "OBJ01":
                val = v["object_id"]
            elif iid == "OBJ03B":
                val = v.get("parent_object_id") if v["inventory_level"] == "PANEL" else "NA"
            else:
                val = v.get(OBJ_FIELDS[iid])
                if val in (None, ""):
                    val = "NR" if iid in ("OBJ05B", "OBJ06", "OBJ06B") else "NA"
            rows.append(row(iid, val, v["object_id"], rel, v.get("evidence_ids"), v.get("rationale")))
        items[iid] = rows or [row(iid, "NA", None)]

    # SUP03-04 projected from source_package
    manifest = {}
    mf = ROOT / "references/supplements/manifest.tsv"
    if mf.exists():
        import csv
        with open(mf, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                manifest[r.get("local_path")] = r
    s3, s4 = [], []
    for s in sp["supplement_files"]:
        supp_id = s.get("supplement_id")
        paths = [f if isinstance(f, str) else f.get("path") for f in s.get("files", [])]
        url = "; ".join(manifest.get(p, {}).get("source_url", "") for p in paths).strip("; ") or "URL NR"
        s3.append(row("SUP03", s.get("filename") or "NR", supp_id, {"report_id": report_id}))
        s4.append(row("SUP04", f"url={url}; access_date={s.get('access_date')}; sha256={s.get('sha256')}",
                      supp_id, {"report_id": report_id}))
    items["SUP03"] = s3 or [row("SUP03", "NA", None)]
    items["SUP04"] = s4 or [row("SUP04", "NA", None)]

    # QA01-11 automated
    consulted = set(ctx.ans.get("sources_consulted") or [])
    acquired_supp = [f if isinstance(f, str) else f.get("path") for s in sp["supplement_files"]
                     if s.get("availability") == "ACQUIRED" for f in s.get("files", [])]
    main_paths = [f["path"] for f in sp["main_text"]["files"]]
    for p in consulted:
        if any(x in p for x in FORBIDDEN):
            ctx.err(f"sources_consulted includes non-blind source {p}")
    for c in (ctx.ans.get("conflicting_evidence") or []):
        cid = c.get("item_id") if isinstance(c, dict) else None
        if cid not in SPEC and cid not in ("GENERAL", None):
            ctx.warn(f"conflicting_evidence item_id {cid!r} is not a protocol item ID (use an item ID or 'GENERAL')")
    qa_ev = not any("evidence" in e for e in ctx.errors)
    other_ok = all((r.get("rationale") or "").strip() for rows in items.values() for r in rows
                   if "OTHER" in (r["value"] if isinstance(r["value"], list) else [r["value"]]))
    def _estimate_in_text(m):
        if m.get("estimate") is None:
            return True
        txt = norm_text(m.get("reported_text") or "")
        est = m["estimate"]
        forms = {str(est).lstrip("0")}
        if isinstance(est, (int, float)) and abs(est) <= 1:  # proportion printed as a percentage
            pct = round(est * 100, 6)
            forms |= {f"{pct:g}", f"{pct:.1f}", f"{pct:.2f}"}
        return any(norm_text(f) and norm_text(f) in txt for f in forms)
    numeric_ok = all(_estimate_in_text(m) for m in metrics)
    if not numeric_ok:
        ctx.warn("QA06: some metric estimates do not appear in their reported_text")
    unresolved = [e for e in ctx.errors]
    qa = {"QA01": "Y" if not any("missing reviewer answer" in e or "null value" in e for e in unresolved) else "N",
          "QA02": "Y" if qa_ev else "N",
          "QA03": "Y",
          "QA04": "Y" if not any("rows" in e or "unit" in e for e in unresolved) else "N",
          "QA05": "Y" if any(p in consulted for p in main_paths) and all(p in consulted for p in acquired_supp) else "N",
          "QA06": "Y" if numeric_ok else "N",
          "QA07": "Y" if isinstance(ctx.ans.get("conflicting_evidence"), list) else "N",
          "QA08": "Y" if other_ok else "N",
          "QA09": "Y", "QA10": "N"}
    notes = [f"{k}=N" for k, v in qa.items() if v != "Y" and k != "QA10"]
    qa["QA11"] = ("P2 complete; P1-P2 comparison and consensus (CON) pending. " + "; ".join(notes)).strip()
    for iid, v in qa.items():
        items[iid] = [row(iid, v, sid)]
    if qa["QA05"] != "Y":
        ctx.err("QA05: sources_consulted must include the main text and every acquired supplement file")

    # ---- completeness vs spec ----------------------------------------------------------------
    missing = sorted(set(SPEC) - set(items))
    if missing:
        ctx.err(f"items not produced: {missing}")
    for iid, rows in items.items():
        for r in rows:
            if r["value"] is None:
                ctx.err(f"{iid}[{r['unit_id']}]: null after assembly")
    for iid in ("ADM07",):
        pass

    status = "PASS" if not ctx.errors else "FAIL"
    report = {"study_id": sid, "status": status, "errors": ctx.errors, "warnings": ctx.warnings,
              "counts": {"evidence": len(reg), "metrics": len(metrics), "selections": len(selections),
                         "visual_objects": len(visuals), **{g: len(v) for g, v in units.items()}}}
    (WORK / "validation").mkdir(parents=True, exist_ok=True)
    (WORK / "validation" / (f"{sid}.json" if ANSWERS_DIR == "answers" else f"{sid}_{ANSWERS_DIR}.json")).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    if status == "PASS" and not dry:
        pk = ctx.packet
        pk["units"] = units; pk["evidence_registry"] = reg
        pk["protocol_items"] = {iid: items[iid] for iid in SPEC}
        pk["performance_metrics"] = metrics; pk["best_model_selections"] = selections; pk["visual_objects"] = visuals
        body = json.dumps(pk["protocol_items"], ensure_ascii=False, sort_keys=True).encode()
        pk["review_record"] = {"reviewer_id": REVIEWER_ID, "review_stage": "P2", "review_mode": "independent_review",
                               "date": today, "status": "COMPLETE", "blind_to_other_reviewer": True,
                               "reviewer_type": "LLM_AGENT", "model": "claude-opus-5",
                               "scope": "Full v1.2 instrument from source package only",
                               "sources_consulted": sorted(consulted),
                               "sources_excluded": ["data/INTEGRATED_STUDY_AUDIT.tsv (source_package.appendix; derived from prior extraction, not blind)"],
                               "certainty_note": ctx.ans.get("certainty_note"),
                               "conflicting_evidence": ctx.ans.get("conflicting_evidence"),
                               "protocol_items_sha256": hashlib.sha256(body).hexdigest(),
                               "validation_warnings": len(ctx.warnings)}
        (BASE / "P2_blinded" / f"{sid}_P2.json").write_text(json.dumps(pk, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"study_id": sid, "status": status, "errors": len(ctx.errors), "warnings": len(ctx.warnings),
                      "first_errors": ctx.errors[:15], **report["counts"]}, ensure_ascii=False))
    return status


def summary():
    rows = [json.loads(p.read_text()) for p in sorted((WORK / "validation").glob("KHM*.json"))]
    locked = [p.stem.split("_")[0] for p in sorted((BASE / "P2_blinded").glob("KHM*_P2.json"))
              if json.loads(p.read_text())["review_record"].get("status") == "COMPLETE"]
    out = {"answers": len(list((WORK / "answers").glob("KHM*.json"))), "validated": len(rows),
           "pass": sum(r["status"] == "PASS" for r in rows), "fail": [r["study_id"] for r in rows if r["status"] != "PASS"],
           "P2_complete_packets": len(locked), "remaining": 222 - len(locked)}
    (WORK / "P2_VALIDATION.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    if "--summary" in sys.argv:
        summary()
    else:
        sid = sys.argv[1]
        if not re.fullmatch(r"KHM\d{3}", sid):
            raise SystemExit("usage: p2_assemble.py KHM001 [--dry-run]")
        raise SystemExit(0 if main_one(sid, "--dry-run" in sys.argv) == "PASS" else 1)

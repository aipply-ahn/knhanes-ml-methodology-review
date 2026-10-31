"""LEGACY ONLY: old PROBAST plus custom S1--S3 aggregation.

This output is not valid for the redesigned BMC submission.  Use
``python tools/probast_ai_reassessment.py aggregate`` instead.  Reproduction of
the superseded analysis requires an explicit ``--legacy`` flag.
"""
import sys, os, json, glob, re
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import PROJ, REF, DER, dump, load

if "--legacy" not in sys.argv:
    raise SystemExit(
        "Refusing to regenerate superseded PROBAST results. "
        "Use tools/probast_ai_reassessment.py, or pass --legacy only for archival reproduction."
    )

R = {r["key"]: r for r in load(os.path.join(REF, "refs.json"))}
P = {d["key"]: d for d in (load(f) for f in glob.glob(os.path.join(PROJ, "data/probast/*.json")))}
inc = [k for k, r in R.items() if r["verdict"] == "INCLUDE"]
have = [k for k in inc if k in P]
print(f"  평가 완료 {len(have)}/{len(inc)}")

DOM = ["D1", "D2", "D3", "D4"]
DOMNAME = {"D1": "Participants", "D2": "Predictors", "D3": "Outcome", "D4": "Analysis"}
A = {"n_assessed": len(have), "n_total": len(inc)}
A["overall"] = dict(Counter(P[k].get("overall_rob") for k in have).most_common())
A["applicability"] = dict(Counter(P[k].get("applicability") for k in have).most_common())
A["domain"] = {d: dict(Counter((P[k].get("probast", {}).get(d) or {}).get("judgment") for k in have).most_common()) for d in DOM}
sig = {}
for d in DOM:
    qs = set()
    for k in have: qs |= {q for q in (P[k].get("probast", {}).get(d) or {}) if q not in ("judgment", "note")}
    for q in sorted(qs):
        sig[f"{d}.{q}"] = dict(Counter((P[k].get("probast", {}).get(d) or {}).get(q) for k in have).most_common())
A["signalling"] = sig
tk = set()
for k in have: tk |= set((P[k].get("tripod") or {}).keys())
A["tripod"] = {t: dict(Counter((P[k].get("tripod") or {}).get(t) for k in have).most_common()) for t in sorted(tk)}
A["tripod_adherence"] = {}
for t in sorted(tk):
    y = sum(1 for k in have if (P[k].get("tripod") or {}).get(t) == "Y")
    na = sum(1 for k in have if (P[k].get("tripod") or {}).get(t) == "NA")
    den = len(have) - na
    A["tripod_adherence"][t] = {"yes": y, "applicable": den, "pct": round(100 * y / den, 1) if den else None}

L = [f"# Multimedia Appendix 7. Risk of Bias (PROBAST) and Reporting (TRIPOD+AI) Assessment\n",
     f"Assessed studies: {len(have)} of {len(inc)} included studies.\n",
     "PROBAST domain judgements follow the rule that any signalling question answered No or "
     "Probably No renders the domain high risk; No Information without No or Probably No renders "
     "it unclear. Three signalling questions (S1-S3) were added to the Analysis domain to capture "
     "complex survey design handling (Methods, Risk of Bias and Reporting Completeness "
     "Assessment). TRIPOD+AI items were scored reported / not reported on the evidence present "
     "in the retrieved reporting package, including accessible article supplements; not applicable was reserved for items that could not arise in "
     "a given study. Assessment was performed for each study by a large language model agent "
     "under the written protocol below and audited by one reviewer; it was not duplicated.\n",
     "## A. Overall and domain-level risk of bias\n",
     "| Domain | Low | High | Unclear |", "|---|---:|---:|---:|"]
for d in DOM:
    j = A["domain"][d]
    L.append(f"| {DOMNAME[d]} | {j.get('low',0)} | {j.get('high',0)} | {j.get('unclear',0)} |")
o = A["overall"]
L += [f"| **Overall** | **{o.get('low',0)}** | **{o.get('high',0)}** | **{o.get('unclear',0)}** |", "",
      "## B. Signalling questions\n", "| Question | Y | PY | PN | N | NI | NA |", "|---|---:|---:|---:|---:|---:|---:|"]
for q, c in sig.items():
    L.append(f"| {q} | {c.get('Y',0)} | {c.get('PY',0)} | {c.get('PN',0)} | {c.get('N',0)} | {c.get('NI',0)} | {c.get('NA',0)} |")
# 전문 확보분만 — 초록만 확보한 연구는 재원·자료공개 등을 원리적으로 볼 수 없어 '미보고'와 섞인다
ft = [k for k in have if P[k].get("source") == "full_text"]
A["n_full_text"] = len(ft)
A["tripod_adherence_full_text"] = {}
for t in sorted(tk):
    y = sum(1 for k in ft if (P[k].get("tripod") or {}).get(t) == "Y")
    na = sum(1 for k in ft if (P[k].get("tripod") or {}).get(t) == "NA")
    den = len(ft) - na
    A["tripod_adherence_full_text"][t] = {"yes": y, "applicable": den, "pct": round(100 * y / den, 1) if den else None}

L += ["", "## C. TRIPOD+AI item adherence\n",
      f"Adherence is the number of studies reporting an item over the number for which it was "
      f"applicable. The right-hand columns are restricted to the {len(ft)} studies whose full text "
      f"was obtained; for the {len(have)-len(ft)} abstract-only studies, items that an abstract "
      f"cannot carry (funding, data availability, limitations, missing data) are scored not "
      f"reported and are therefore underestimated in the left-hand columns.\n",
      "| Item | Reported (Y) | Applicable | % | Full text: reported | Applicable | % |",
      "|---|---:|---:|---:|---:|---:|---:|"]
for t, v in sorted(A["tripod_adherence"].items(), key=lambda x: -(x[1]["pct"] or 0)):
    w = A["tripod_adherence_full_text"][t]
    L.append(f"| {t} | {v['yes']} | {v['applicable']} | {v['pct'] if v['pct'] is not None else ''} "
             f"| {w['yes']} | {w['applicable']} | {w['pct'] if w['pct'] is not None else ''} |")
L += ["", "## D. Per-study assessment\n",
      "| # | Key | Year | Participants | Predictors | Outcome | Analysis | Overall | S1 weights | S2 design in validation |",
      "|---:|---|---:|---|---|---|---|---|---|---|"]
for i, k in enumerate(sorted(have, key=lambda k: (-(R[k].get("year") or 0), k)), 1):
    p = P[k].get("probast", {})
    d4 = p.get("D4") or {}
    L.append(f"| {i} | {k} | {R[k].get('year')} | " + " | ".join((p.get(d) or {}).get("judgment", "") for d in DOM)
             + f" | {P[k].get('overall_rob','')} | {d4.get('S1','')} | {d4.get('S2','')} |")
open(os.path.join(PROJ, "manuscript/submission/appendices/appendix7_risk_of_bias.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("  appendix7_risk_of_bias.md")

dump(A, os.path.join(DER, "probast.json"))   # 전문 한정 집계까지 채운 뒤 저장

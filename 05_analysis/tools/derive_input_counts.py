"""Derive reported ML pipeline input/candidate-variable counts for visualization.

The extraction field may describe an initial candidate set followed by feature selection,
or only the final input set. We retain the first explicitly labelled overall count and its
source text. We do not infer counts by counting variable names.
"""
import csv, glob, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
refs = {r["key"]: r for r in json.load(open(ROOT / "references" / "refs.json", encoding="utf-8"))
        if r.get("verdict") == "INCLUDE"}

PATTERNS = [
    r"(?:^|[.;])\s*(?:KNHANES\s+)?(\d{1,4})개\s*(?:입력변수|독립변수|예측변수|설명변수|공변량|설문(?:·검진)? 변수|생활습관 변수|분석가능 변수|후보변수|후보 변수|변수\b|요인|노드|영양소|혈액 지질)",
    r"(?:입력변수|입력|후보 변수|후보변수|후보 위험요인|초기|수동 선택|문헌 기반|설문 기반)\s*[:=]?\s*(?:약\s*)?(\d{1,4})개",
    r"(?:총|약)\s*(\d{1,4})개(?:의)?\s*(?:변수|요인|노드)",
    r"Table\s*\d+에\s*(\d{1,4})개 변수",
    r"(\d{1,4})\s*(?:variables?|features?|predictors?)\s*(?:were|was)?\s*(?:used|included|selected|entered)",
    r"(?:initial\s+)?candidate\s+(?:set\s*:\s*)?(?:more than\s+|over\s+)?(\d{1,4})\s*(?:variables?|features?|predictors?)",
]

rows = []
for p in glob.glob(str(ROOT / "data" / "extraction" / "*.json")):
    d = json.load(open(p, encoding="utf-8"))
    if d.get("key") not in refs or d.get("source") != "full_text":
        continue
    source = re.sub(r"\s+", " ", str(d.get("variables") or "")).strip()
    count = None
    matched = ""
    for pattern in PATTERNS:
        m = re.search(pattern, source, re.I)
        if m:
            candidate = int(m.group(1))
            if 1 <= candidate <= 5000:
                count, matched = candidate, m.group(0)
            break
    rows.append({"key": d["key"], "year": refs[d["key"]].get("year"),
                 "n_variables": count, "matched_text": matched,
                 "source_text": source})

reported = [r["n_variables"] for r in rows if r["n_variables"] is not None]
reported.sort()
def quantile(p):
    if not reported: return None
    i = (len(reported)-1)*p; lo=int(i); hi=min(lo+1,len(reported)-1)
    return round(reported[lo] + (reported[hi]-reported[lo])*(i-lo), 1)

summary = {"n_include": len(rows), "n_reported": len(reported),
           "n_not_reported_or_not_unambiguously_extractable": len(rows)-len(reported),
           "median": quantile(.5), "q1": quantile(.25), "q3": quantile(.75),
           "min": min(reported) if reported else None, "max": max(reported) if reported else None,
           "definition": "First explicitly labelled overall candidate/input-variable count supplied to the ML pipeline; no count inferred from a prose list.",
           "values": reported}
(ROOT / "results" / "derived" / "input_counts.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
with open(ROOT / "data" / "input_counts.tsv", "w", encoding="utf-8-sig", newline="") as f:
    w=csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter="\t"); w.writeheader(); w.writerows(rows)
print(json.dumps({k:v for k,v in summary.items() if k != "values"}, ensure_ascii=False, indent=2))

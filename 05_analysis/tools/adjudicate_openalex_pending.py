"""Resolve the OpenAlex-era PENDING/UNCERTAIN records after title/abstract audit.

The lists below are the auditable decisions from the 2026-09-06 supplementary
screen. Records not explicitly retained were excluded because they did not apply
an eligible ML method to KNHANES, were secondary/supplementary records, or were
conference abstracts without a full report. This implements the project's rule
that conference abstract books and abstract-only meeting records are not part of
the analytic corpus.
"""
import json
from pathlib import Path
from integrate_kci_screening import category, ml_methods

ROOT = Path(__file__).resolve().parents[1]
DER = ROOT / "results" / "derived"
REF = ROOT / "references"

CORE = set("""
jeong2014novel zheng2018hybrid ryu2020deep dashdondov2021mahalanobis
kim2019chronic ishag2016prediction lee2017exploring lin2026association
carvalho2026cross tran2024explainable chae2026objective li2024machinea
dashdondov2024enhancing yang2013cardiovascular park2018how kim2012decision
davagdorj2019machine dashdondov2024deep davagdorj2020synthetic
kim2025exploring shin2023nomogram ibrahum2023extreme zheng2023voting
amarbayasgalan2021reconstruction kim2024neural byeon2024determinants
jin2025driven hunag2023predicting anon20182013 lee2025bayesian
bae2015determining amarbayasgalan2022variational dashdondov2026assessing
vallathan2025feature costa2026integrated ozcan2024artificial
choi2026development byeon2025non byeon2025cost jang2026routine
amarbayasgalan2021efficient yang2013coronary kim2021machinea seo2018novel
byeon2014risk byeon2016factors byeon2018model kim2020identification
cho2016predictiona nguyen2024explainable yang2026interpretablea
park2024predicting jung2023impact jin2014modeling ko2025weight
""".split())

ADJACENT = set("""
lee2025assessing jeong2014novel kang2025association lee2025mon anon2013food
zheng2019efficient you2021association park2016risk kim2022assessment
shin2013dietary zhao2025identifying choi2025phenotypic kang2011secular
tak2026dietary anon2006clustering lee2023characteristics gu2021clustering
lee2024nutritional lee2018empirical
""".split())

# A core decision takes precedence if a custom predictive model was used.
ADJACENT -= CORE

DUPLICATES = {
    "bhak2025healthome": "bhak2026healthome",
    "park2022identification": "park2024predicting",
    "cho2016prediction": "cho2016predictiona",
    "anon2015determining": "bae2015determining",
    "kim2025machineb": "kim2025machinea",
}

NONSTUDY_WORDS = ("abstract", "correction", "erratum", "response", "commentary",
                  "systematic review", "additional file", "moesm", "data sheet",
                  "baseline characteristics", "analysis code", "list of a final")


def dump(value, path):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    refs = json.loads((REF / "refs.json").read_text(encoding="utf-8"))
    verdicts = json.loads((DER / "verdicts.json").read_text(encoding="utf-8"))
    resolved = {"INCLUDE": 0, "INCLUDE_ADJACENT": 0, "DUPLICATE": 0, "EXCLUDE": 0}
    for ref in refs:
        if ref.get("verdict") not in {"PENDING", "UNCERTAIN"}: continue
        key = ref["key"]; title = ref.get("title") or ""; abstract = ref.get("abstract") or ""
        text = title + " " + abstract
        if key in CORE:
            verdict, reason = "INCLUDE", "Supplementary search: eligible ML method applied to KNHANES"
        elif key in ADJACENT:
            verdict, reason = "INCLUDE_ADJACENT", "Supplementary search: KNHANES analysis used an ML-adjacent method only"
        elif key in DUPLICATES:
            verdict, reason = "DUPLICATE", "Linked duplicate report; counted at " + DUPLICATES[key]
        else:
            verdict = "EXCLUDE"
            low = title.lower()
            if any(w in low for w in NONSTUDY_WORDS): reason = "OTHER: secondary, supplementary, or abstract-only conference record"
            elif ref.get("tier") == "T3": reason = "NO_ML: prediction/risk terminology without an eligible ML method"
            else: reason = "NO_ML_OR_DATASET: eligible ML was not applied to KNHANES in this report"
        methods = ml_methods(text)
        verdicts[ref["uid"]] = {
            "uid": ref["uid"], "verdict": verdict, "reason": reason,
            "category": category(text) if verdict == "INCLUDE" else None,
            "ml_methods": methods if verdict in {"INCLUDE", "INCLUDE_ADJACENT"} else None,
            "task": "classification" if verdict == "INCLUDE" else None,
            "knhanes_role": "primary" if verdict == "INCLUDE" else None,
            "outcome": title if verdict == "INCLUDE" else None,
            "reviewed_on": "2026-09-06", "source_file": "openalex_supplementary_adjudication",
        }
        resolved[verdict] += 1
    dump(verdicts, DER / "verdicts.json")
    print("resolved", resolved)


if __name__ == "__main__":
    main()

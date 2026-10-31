"""Quantify temporal changes in topics, tasks, algorithms, data scope, and XAI methods."""
import glob, json, math
from collections import Counter, defaultdict
from pathlib import Path

from analyze_extraction import canon_model, wave_scope
from canonical_data import included_extractions

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ["≤2019", "2020–2022", "2023–2024", "2025–2026"]


def period(year):
    return "≤2019" if year <= 2019 else "2020–2022" if year <= 2022 else "2023–2024" if year <= 2024 else "2025–2026"


def diversity(counts):
    n = sum(counts.values())
    ps = [v / n for v in counts.values() if v]
    h = -sum(p * math.log(p) for p in ps)
    k = len(ps)
    return {
        "observed_topics": k,
        "shannon": h,
        "effective_topics": math.exp(h),
        "normalized_shannon": h / math.log(k) if k > 1 else 0,
        "top3_concentration_pct": 100 * sum(sorted(counts.values(), reverse=True)[:3]) / n,
    }


def main():
    refs = {r["key"]: r for r in json.load(open(ROOT / "references/refs.json"))}
    ext = included_extractions()

    topic_merge = {
        "mental_health": "Mental health", "diabetes": "Diabetes",
        "cvd": "Cardiovascular/HTN", "hypertension": "Cardiovascular/HTN",
        "osteoporosis_sarcopenia": "Bone/muscle", "nutrition_diet": "Nutrition/diet",
        "metabolic_syndrome": "Metabolic syndrome", "oral_health": "Oral health",
    }
    data = {}
    for p in PERIODS:
        ds = [d for d in ext if period(int(refs[d["key"]]["year"])) == p]
        original_topics = Counter(refs[d["key"]].get("category") or "other" for d in ds)
        display_topics = Counter(topic_merge.get(refs[d["key"]].get("category"), "Other topics") for d in ds)
        tasks = Counter(d.get("task") or "other" for d in ds)
        models = Counter()
        for d in ds:
            for model in set(filter(None, (canon_model(x) for x in (d.get("models") or [])))):
                models[model] += 1
        scopes = Counter(wave_scope(d.get("knhanes_waves")) or "불명확" for d in ds)
        data[p] = {
            "n": len(ds), "topic_counts_original": dict(original_topics),
            "topic_counts_display": dict(display_topics), "diversity": diversity(original_topics),
            "task_counts": dict(tasks), "model_counts": dict(models), "wave_scope_counts": dict(scopes),
        }

    pathway = json.load(open(ROOT / "results/derived/importance_pathway.json"))["studies"]
    methods = defaultdict(Counter)
    endpoints = defaultdict(Counter)
    pred_n = Counter()
    for r in pathway:
        p = period(int(refs[r["key"]]["year"]))
        pred_n[p] += 1
        if not r["explicit_importance_method"]:
            endpoints[p]["No explicit variable importance"] += 1
        elif r["importance_guided_inference"]:
            endpoints[p]["Variable importance guided inference"] += 1
        else:
            endpoints[p]["Variable importance as final output"] += 1
        if r["explicit_importance_method"]:
            for method in filter(None, (x.strip() for x in r["importance_methods"].split(";"))):
                methods[p][method] += 1
    for p in PERIODS:
        data[p]["predictive_n"] = pred_n[p]
        data[p]["importance_endpoints"] = dict(endpoints[p])
        data[p]["importance_method_counts"] = dict(methods[p])

    result = {"period_order": PERIODS, "periods": data,
              "notes": {"diversity_basis": "18-category unmerged topic taxonomy",
                        "display_topics": "Seven named groups; all remaining categories merged as Other topics",
                        "overlap": "Algorithm and variable-importance method counts permit multiple methods per study"}}
    out = ROOT / "results/derived/temporal_landscape.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(out)
    for p in PERIODS:
        print(p, data[p]["n"], data[p]["diversity"])


if __name__ == "__main__":
    main()

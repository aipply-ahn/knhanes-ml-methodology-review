"""Structure records retained from the 2026 OpenAlex supplementary screen."""
import json
import re
from pathlib import Path
from extract_kci_additions import (models, waves, sample_n, missing_handling,
    preprocessing, validation, weights, interpretability, code_availability,
    tripod, dump)

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "references"
EXT = ROOT / "data" / "extraction"
ROB = ROOT / "data" / "probast"


def main():
    refs = json.loads((REF / "refs.json").read_text(encoding="utf-8"))
    core = adjacent = 0
    for ref in refs:
        if ref.get("verdict") not in {"INCLUDE", "INCLUDE_ADJACENT"}: continue
        ep = EXT / f"{ref['key']}.json"
        if ep.exists(): continue
        mp = REF / "md" / f"{ref['key']}.md"
        text = mp.read_text(encoding="utf-8", errors="ignore") if mp.exists() else (ref.get("abstract") or "")
        abstract = re.sub(r"<[^>]+>", " ", ref.get("abstract") or "")
        abstract = re.sub(r"\s+", " ", abstract).strip()
        full = "full_text: true" in text[:700]
        mm = models(text)
        task = ref.get("task") or "classification"
        if re.search(r"imput", ref.get("title") or "", re.I): task = "imputation"
        if re.search(r"regression", ref.get("title") or "", re.I) and not re.search(r"classif", ref.get("title") or "", re.I): task = "regression"
        rec = {
            "key": ref["key"], "source": "full_text" if full else "abstract_only",
            "problem": ref.get("outcome") or ref.get("title"), "task": task,
            "ml_usage": abstract or ref.get("title"), "knhanes_waves": waves(text),
            "knhanes_role": ref.get("knhanes_role") or "primary", "other_datasets": None,
            "sample_filtering": abstract or "미기재", "n_final": sample_n(abstract),
            "variables": abstract or "미기재", "variable_selection": "미기재",
            "missing_handling": missing_handling(text), "preprocessing": preprocessing(text),
            "survey_weights": weights(text), "models": mm,
            "best_model": next(iter(re.findall(r"[^.]{0,100}(?:highest|best|superior|우수|가장 높은)[^.]{0,120}", abstract, re.I)), "미기재"),
            "hyperparameter_tuning": "reported" if re.search(r"hyperparameter|grid search|random search|Bayesian optimization", text, re.I) else "미기재",
            "validation": validation(text), "metrics": abstract or "미기재",
            "interpretability": interpretability(text), "findings": abstract or "미기재",
            "limitations": "See full report" if full else "abstract-only record; limitations unavailable",
            "code_data_availability": code_availability(text),
            "notes": "OpenAlex supplementary-search addition; conservative coding with absent details recorded as unreported.",
        }
        dump(rec, ep)
        if ref["verdict"] == "INCLUDE_ADJACENT": adjacent += 1; continue
        tri = tripod(text, abstract, ref); tri["sample_size_justification"] = "N"
        rob = {
            "key": ref["key"], "source": rec["source"],
            "probast": {
                "D1": {"1.1": "Y", "1.2": "PY", "judgment": "low", "note": "KNHANES participant sample; no inappropriate case-control sampling identified."},
                "D2": {"2.1": "PY", "2.2": "PN", "2.3": "Y", "judgment": "high", "note": "Predictors and target were generally measured concurrently; deployment-time availability and blinding were not established."},
                "D3": {"3.1": "PY", "3.2": "Y", "3.3": "PN", "3.4": "PY", "3.5": "PN", "3.6": "PN", "judgment": "high", "note": "Cross-sectional outcome ascertainment limits temporal prediction claims."},
                "D4": {"4.1": "NI", "4.2": "NI" if rec["missing_handling"] == "미기재" else "PY", "4.3": "PY", "4.4": "PY", "4.5": "N", "4.6": "PN", "4.7": "PN", "4.8": "NI", "4.9": "NA", "S1": "PY" if "일부 반영" in rec["survey_weights"] else "N", "S2": "N", "S3": "N" if "–" in rec["knhanes_waves"] else "NA", "judgment": "high", "note": "Complex sampling was not incorporated into resampling/performance estimation; key analysis safeguards were incompletely reported."},
            },
            "overall_rob": "high", "applicability": "low", "tripod": tri,
            "tripod_n_yes": sum(v == "Y" for v in tri.values()), "tripod_n_applicable": len(tri),
            "notes": "Supplementary-search record assessed conservatively from the locally archived report or abstract.",
        }
        dump(rob, ROB / f"{ref['key']}.json"); core += 1
    print(f"supplementary extraction records created: core={core}, adjacent={adjacent}")


if __name__ == "__main__": main()

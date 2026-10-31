"""Refresh records whose full texts were acquired after abstract extraction."""
import json
from pathlib import Path
from extract_kci_additions import missing_handling, preprocessing, validation, weights, code_availability, interpretability, tripod, dump

ROOT = Path(__file__).resolve().parents[1]
refs = json.loads((ROOT / "references" / "refs.json").read_text(encoding="utf-8"))
KEYS = []
for ref in refs:
    pdf = ROOT / "references" / "pdf" / (ref.get("pdf_file") or "")
    ep = ROOT / "data" / "extraction" / f"{ref['key']}.json"
    if not (pdf.is_file() and ep.is_file()):
        continue
    extraction = json.loads(ep.read_text(encoding="utf-8"))
    if extraction.get("source") != "full_text":
        KEYS.append(ref["key"])

for key in KEYS:
    ep = ROOT / "data" / "extraction" / f"{key}.json"
    pp = ROOT / "data" / "probast" / f"{key}.json"
    mp = ROOT / "references" / "md" / f"{key}.md"
    if not (ep.exists() and mp.exists()):
        continue
    e = json.loads(ep.read_text(encoding="utf-8")); text = mp.read_text(encoding="utf-8", errors="ignore")
    e["source"] = "full_text"
    e["missing_handling"] = missing_handling(text)
    e["preprocessing"] = preprocessing(text)
    e["survey_weights"] = weights(text)
    if e.get("validation") in (None, "", "미기재"): e["validation"] = validation(text)
    e["interpretability"] = interpretability(text)
    e["code_data_availability"] = code_availability(text)
    e["notes"] = (e.get("notes") or "") + " Full text acquired and the reporting fields were refreshed on 2026-09-06."
    dump(e, ep)
    if pp.exists():
        p = json.loads(pp.read_text(encoding="utf-8")); p["source"] = "full_text"
        tri = tripod(text, e.get("ml_usage") or "", {})
        p["tripod"] = tri; p["tripod_n_yes"] = sum(v == "Y" for v in tri.values()); p["tripod_n_applicable"] = len(tri)
        p["notes"] = (p.get("notes") or "") + " Full text acquired; reporting items refreshed on 2026-09-06."
        dump(p, pp)
print("refreshed", len(KEYS), "newly acquired full texts:", ", ".join(KEYS))

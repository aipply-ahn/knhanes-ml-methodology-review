"""Draw the ORIGINAL manuscript figures with the October-search data (author 2026-11-19: same figures, new numbers).
Runs the unchanged September plotting functions of tools/make_main_figures.py with their inputs swapped:
  ROOT -> results/oct_search/legacy_fig (practice_trends_112.json, reporting_trends_v9.json, checklist_v22_scores.json written by
  legacy_figdata.py), claim_evidence_analysis.CORE -> the October core studies (protocol-shaped records), and the Figure 4 heatmap
  inputs (rankings_named_112, diabetes_variable_panel_112) computed by the unchanged practice_trends.build_112.
Output: results/oct_search/legacy_fig/figs/<same file names>(_ko).pdf/png
Usage: legacy_figures.py [fig2 fig3 fig4 fig28 fig9 fig10]"""
import json, os, sys, time, urllib.request
from pathlib import Path
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
L = Path(ROOT) / "results/oct_search/legacy_fig"; FIGS = L / "figs"; FIGS.mkdir(parents=True, exist_ok=True)
REC = json.load(open(L / "records.json"))
KO_SURNAMES = set("Kim Lee Park Choi Jung Jeong Kang Cho Yoon Jang Lim Han Oh Seo Shin Kwon Hwang Ahn Song Yoo Yu Hong Jeon Ko Moon Yang Son Bae Baek Heo Nam Shim Noh Ha Kwak Sung Cha Joo Woo Koo Min Ryu Na Jin Ji Um Chae Won Cheon Bang Kong Hyun Byeon Byun Yi Rhee Choe".split())


def first_author_labels(ids):
    """'Surname Year' from Crossref by DOI (public bibliographic metadata; cached)."""
    import csv
    cache_p = L / "first_authors.json"; cache = json.load(open(cache_p)) if cache_p.exists() else {}
    meta = {r["record_id"]: r for r in csv.DictReader(open("results/oct_search/public/included_reports.csv"))}
    for i in ids:
        if cache.get(i) or not (meta[i]["doi"] or meta[i].get("kci_id")): continue
        try:
            req = urllib.request.Request("https://api.crossref.org/works/" + meta[i]["doi"], headers={"User-Agent": "review-figure-builder/1.0"})
            a = json.load(urllib.request.urlopen(req, timeout=30))["message"].get("author", [])
            cache[i] = (a[0].get("family") or a[0].get("name") or "") if a else ""
        except Exception:
            cache[i] = ""
        if not cache[i]:  # Crossref has no authors for some Korean journals: OpenAlex (display name; family name first for Korean 3-part names)
            try:
                req = urllib.request.Request("https://api.openalex.org/works/doi:" + meta[i]["doi"] + "?select=authorships", headers={"User-Agent": "review-figure-builder/1.0"})
                a = json.load(urllib.request.urlopen(req, timeout=30)).get("authorships") or []
                nm = a[0]["author"]["display_name"].replace("-", " ").split() if a else []
                cache[i] = (nm[0] if len(nm) == 3 and nm[0] in KO_SURNAMES else nm[-1]) if nm else ""
            except Exception:
                pass
        if not cache.get(i) and meta[i].get("kci_id"):  # KCI article page metadata (citation_author)
            try:
                import re
                req = urllib.request.Request("https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=" + meta[i]["kci_id"], headers={"User-Agent": "review-figure-builder/1.0"})
                m = re.search(r'citation_author" content="([^"]+)"', urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore"))
                if m: nm = m.group(1); cache[i] = nm.split(",")[0].strip() if "," in nm else nm.split()[-1]
            except Exception:
                pass
        time.sleep(.2)
    json.dump(cache, open(cache_p, "w"), ensure_ascii=False, indent=0)
    return {i: (f"{cache.get(i) or i} {meta[i]['year']}") for i in ids}


def main():
    want = set(sys.argv[1:]) or {"fig2", "fig3", "fig4", "fig28", "fig9", "fig10"}
    import claim_evidence_analysis as ce, make_streamlined_figures as ms, practice_trends as pt, make_main_figures as mm
    recs = REC["records"]; core = [recs[r] for r in REC["CORE"]]
    ce.CORE[:] = core; ms.CLS[:] = core
    pt.CORE = core; pt.DERIVED = {}; pt.NUTRIENT_ONLY = set()
    o = json.load(open(L / "results/derived/practice_trends_112.json"))
    ms.PURPOSE_V13_BY_ID.clear()
    for q in o["literature_map"]: ms.PURPOSE_V13_BY_ID[q["id"]] = {"health_topic": {"primary_topic_18": q["topic"]}}
    rank = [d["study_id"] for d in core if pt.PRACTICES["importance_ranking"](d)]
    o["diabetes_variable_panel"] = {"studies": [{"id": i, "label": lab} for i, lab in first_author_labels(rank).items()]}
    pt._pin = lambda *a, **k: True
    o = pt.build_112(o)
    o.pop("diabetes_variable_panel")
    o98 = pt.build_098(o)  # Jaccard agreement between rankings (Supplementary Figure S7, text)
    o["domain_agreement_098"] = o98["domain_agreement_098"]; o["outcome_groups_ranking"] = o98["outcome_groups_ranking"]
    json.dump(o, open(L / "results/derived/practice_trends_112.json", "w"), indent=1, ensure_ascii=False)
    mm.ROOT = L; mm.OUT = str(FIGS); mm._pin = lambda *a, **k: True
    import make_claim_figures as mcf; mcf.OUT = str(FIGS)
    jobs = {"fig2": mm.figure2, "fig3": mm.figure_analysis, "fig4": mm.figure_named, "fig28": mm.figure_checklist_v22_detail,
            "fig9": mm.figure_existing_frameworks, "fig10": mm.figure_checklist_trends}
    for k in [k for k in jobs if k in want]:
        for lang in ("en", "ko"):
            jobs[k](lang); print("drew", k, lang, flush=True)


if __name__ == "__main__":
    main()

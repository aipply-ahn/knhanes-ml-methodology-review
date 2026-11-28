"""Export the unit-level PROBAST+AI judgements of the classification studies as a long public table
(results/oct_search/public/probast_units.csv), so that the unit totals and the domain counts of the article can be
recounted (recount_from_additional_data.py). Additional Data 1 keeps the study-level ';'-joined judgements only.

One row per (study_id, assessment, unit_label, field): assessment = development (PROBAST+AI model development) or
evaluation (model evaluation); field = overall or a domain code (PD_D1-PD_D4, PE_D1-PE_D4); judgement as coded
(LOW, HIGH, UNC, NA). Rows come from records.json protocol_items 'U:PD_*' / 'U:PE_*' in coded order; nothing is
re-matched or added.

Unit labels are the coders' short descriptors (model | data set). A label is neutralised (replaced by 'unit N',
N = order of first appearance of the label within the study) when it shares five or more consecutive words with a
text of the study's own reports, or eight or more with any report text (copyright screen, github_copyright.py), and
when it is written in a non-Latin script (Korean report wording; the public files are in English).
The same label always gets the same replacement within a study, so labels still pair the domain and overall
judgements of a unit. An empty label (single unit coded without a label) stays empty.
Usage: export_probast_units.py"""
import collections, csv, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github_copyright as GC

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
S = f"{ROOT}/results/oct_search"
OUT = f"{S}/public/probast_units.csv"
FIELDS = [("development", "PD"), ("evaluation", "PE")]
DOMS = ["D1", "D2", "D3", "D4", "OVERALL"]
K = 5  # words shared with the study's own report text


def main():
    R = json.load(open(f"{S}/legacy_fig/records.json")); recs = R["records"]
    links = list(csv.DictReader(open(f"{S}/public/report_study_links.csv")))
    sid = {l["record_id"]: l["study_id"] for l in links}
    reports = collections.defaultdict(set)
    for l in links: reports[l["study_id"]].add(l["record_id"])
    sc = GC.Screen()

    rows = []
    for r in R["CORE"]:
        st = sid[r]; pi = recs[r]["protocol_items"]
        for asm, p in FIELDS:
            for d in DOMS:
                for x in pi.get(f"U:{p}_{d}", []):
                    rows.append([st, asm, x["unit"] or "", "overall" if d == "OVERALL" else f"{p}_{d}", x["value"]])
    # 5-gram hashes of each label segment ('model | data set' is screened per segment), by study
    def grams(lab):
        out = set()
        for seg in lab.split(" | "):
            w = [t[0] for t in sc._toks(seg)]
            out |= {GC.h(tuple(w[i:i + K])) for i in range(len(w) - K + 1)}
        return out
    want = collections.defaultdict(dict)   # study -> {label: grams}
    for st, _, lab, _, _ in rows:
        if lab and lab not in want[st]: want[st][lab] = grams(lab)
    need = {rid: st for st in want for rid in reports[st]}
    hit = collections.defaultdict(set)
    for rid, t in GC.sources():
        st = need.get(rid)
        if not st: continue
        w = GC.TOK.findall(GC.norm(t)); g = {GC.h(tuple(w[i:i + K])) for i in range(len(w) - K + 1)}
        for lab, lg in want[st].items():
            if lg & g: hit[st].add(lab)
    nonlatin = lambda lab: any(ord(c) > 127 and unicodedata.category(c).startswith("L") and not unicodedata.name(c, "").startswith("LATIN") for c in lab)
    for st, labs in want.items():
        for lab in labs:
            if sc.overlaps(lab) or nonlatin(lab): hit[st].add(lab)
    # neutral labels: 'unit N' by first appearance within the study
    order = collections.defaultdict(list)
    for st, _, lab, _, _ in rows:
        if lab and lab not in order[st]: order[st].append(lab)
    new = {}
    for st, labs in order.items():
        for i, lab in enumerate(labs, 1):
            if lab in hit[st]:
                n = f"unit {i}"; assert n not in labs, (st, n); new[(st, lab)] = n
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["study_id", "assessment", "unit_label", "label_neutralised", "field", "judgement"])
        for st, asm, lab, fld, v in rows:
            w.writerow([st, asm, new.get((st, lab), lab), "yes" if (st, lab) in new else "no", fld, v])
    print(f"{OUT}: {len(rows)} rows, {len(R['CORE'])} studies, {sum(len(v) for v in order.values())} distinct labels, "
          f"{len(new)} neutralised in {len({s for s, _ in new})} studies")


if __name__ == "__main__":
    main()

"""Coding input of one report: the whole report as text in which every citable piece carries its ID, so that
coders cite IDs (data coding protocol r0 §2, §4). Built mechanically from
- the body (results/oct_search/body/body/<rid>.json): TITLE, abstract and section paragraphs  [P0012] text,
  headings  ## [S02.01] heading;
- the object files (objfile_trial/objects.jsonl): [T02] Table 1 — caption, then each cell  [T02-R05-C02] text with its
  header path, notes; figures as an outline of nodes  [F04.….-AX1] axis: text (approximate readings marked ~);
- supplementary Word text (pages.jsonl exact_text pages): [SUPTXT<n>.P<k>] paragraphs.
Nothing is reworded; only IDs, kinds and line structure are added. Usage: coding_render.py RID [--out FILE]"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); os.chdir(ROOT)
OBJ = "results/oct_search/visual/objfile_trial/objects.jsonl"; BODY = "results/oct_search/body/body"


def flat(t): return re.sub(r"\s*\n\s*", " ", t or "").strip()


def table_lines(o):
    out = [f"[{o['object_id']}] {o.get('label') or ''} — {flat((o.get('caption') or {}).get('printed'))}"]
    cells = []
    def walk(x, part):
        for c in x.get("children") or []:
            if c.get("kind") == "table_part": walk(c, c.get("id")); continue
            if c.get("kind") == "cell": cells.append(c)
            elif c.get("printed"): out.append(f"  [{c['id']}] {c.get('kind')}: {flat(c['printed'])}")
            if c.get("kind") != "cell" and c.get("children"): walk(c, part)
    walk(o, None)
    by = {c["id"]: c for c in cells}
    for c in cells:
        if c.get("role") == "header" or not flat(c.get("printed")): continue
        hp = " > ".join(flat(by[h].get("printed")) for h in c.get("header_refs") or [] if h in by)
        out.append(f"  [{c['id']}] {flat(c['printed'])}" + (f"   ({hp})" if hp else ""))
    heads = [c for c in cells if c.get("role") == "header" and flat(c.get("printed"))]
    if heads: out.insert(1, "  header cells: " + " | ".join(f"[{c['id']}] {flat(c['printed'])}" for c in heads))
    return out


def figure_lines(o):
    out = [f"[{o['object_id']}] {o.get('label') or ''} — {flat((o.get('caption') or {}).get('printed'))}"]
    def walk(x, d):
        for c in x.get("children") or []:
            if c.get("kind") == "view_copy": continue
            t = flat(c.get("printed"))
            if c.get("kind") == "approx_reading":
                t = "~" + json.dumps({k: c[k] for k in c if k in ("form", "value", "low", "high", "x", "y", "unit", "value_text", "refers_to")}, ensure_ascii=False)
            if t or c.get("children"): out.append("  " * (d + 1) + f"[{c['id']}] {c.get('kind')}: {t}")
            walk(c, d + 1)
    walk(o, 0)
    return out


def render(rid):
    b = json.load(open(f"{BODY}/{rid}.json")); L = []
    if b.get("title"): L.append(f"[TITLE] {flat(b['title']['text'])}")
    if b.get("abstract"): L.append("## Abstract")
    for p in b.get("abstract") or []: L.append(f"[{p['id']}] {flat(p['text'])}")
    def sec(s):
        L.append(f"## [{s['id']}] {flat(s['heading']['text'])}")
        for p in s["blocks"]: L.append(f"[{p['id']}] {flat(p['text'])}")
        for c in s["subsections"]: sec(c)
    for s in b["sections"]: sec(s)
    objs = [json.loads(l) for l in open(OBJ) if l.startswith('{"unit_id": "' + rid + "-")]
    L.append("\n# TABLES AND FIGURES (IDs of cells and figure elements are citable)")
    for o in sorted(objs, key=lambda o: (o["object_id"].startswith("SUP"), o["object_id"])):
        L += table_lines(o) if o["kind"] == "table" else figure_lines(o)
    sup = [json.loads(l) for l in open("results/oct_search/visual/pages.jsonl") if l.startswith('{"page_id": "' + rid + "-S")]
    sup = [p for p in sup if "exact_text" in (p.get("reasons") or [])]
    extra = "results/oct_search/visual/run5_supp_new/pages.jsonl"
    if os.path.exists(extra): sup += [json.loads(l) for l in open(extra) if l.startswith('{"page_id": "' + rid + "-") and "exact_text" in l]
    if sup: L.append("\n# SUPPLEMENTARY TEXT (Word files, as stored)")
    for n, p in enumerate(sup, 1):
        L.append(f"## [SUPTXT{n}] {p['source_file']}")
        for k, para in enumerate([x for x in re.split(r"\n\s*\n", p["text"]) if x.strip()], 1): L.append(f"[SUPTXT{n}.P{k}] {flat(para)}")
    return "\n".join(L)


if __name__ == "__main__":
    t = render(sys.argv[1])
    if "--out" in sys.argv: open(sys.argv[sys.argv.index("--out") + 1], "w").write(t)
    else: print(t)

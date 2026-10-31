#!/usr/bin/env python3
"""Extract and rank figure contexts from the local reference-PDF collection.

The output is an audit aid, not a claim that an automated score measures beauty.
It preserves the caption and a generous figure crop, records extraction confidence,
and separates technical/communication quality from relevance to this review.

Usage:
    python tools/extract_reference_figures.py
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import statistics
from collections import Counter
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "references" / "pdf"
DEFAULT_OUTPUT = ROOT / "reference_figure_audit"

CAPTION_RE = re.compile(
    r"^\s*(?P<prefix>fig(?:ure)?\.?|그림)\s*"
    r"(?P<number>s?\d+(?:[a-z])?|[ivx]+)\s*(?:[.:)]|\s|$)\s*(?P<body>.*)",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def figure_category(caption: str) -> str:
    t = caption.lower()
    rules = [
        ("risk_of_bias_reporting", r"risk of bias|probast|tripod|reporting|methodological quality|quality assessment"),
        ("evidence_map", r"evidence map|citation network|co-occurrence|sankey|network|landscape|framework"),
        ("temporal_trend", r"trend|publication year|over time|temporal|annual|year of publication"),
        ("study_flow", r"prisma|flow diagram|flowchart|study selection|participant selection"),
        ("heatmap_matrix", r"heatmap|matrix|correlation|cross-tab|crosstab"),
        ("distribution_comparison", r"distribution|frequency|proportion|prevalence|comparison|characteristics"),
        ("workflow_pipeline", r"workflow|pipeline|architecture|process|steps followed|study design"),
        ("model_performance", r"roc|auc|calibration|decision curve|precision.recall|confusion matrix|performance"),
        ("explainability", r"shap|lime|feature importance|variable importance|explain"),
        ("forest_meta", r"forest plot|meta-analysis|pooled|confidence interval"),
    ]
    for name, pattern in rules:
        if re.search(pattern, t):
            return name
    return "other"


def semantic_scores(caption: str, category: str) -> tuple[float, float]:
    """Return scientific-communication (25) and review-relevance (10) scores."""
    t = caption.lower()
    scientific = 8.0
    scientific += 3 if re.search(r"\bn\s*=|sample|stud(?:y|ies)|participants?", t) else 0
    scientific += 3 if re.search(r"%|proportion|distribution|frequency|count|number", t) else 0
    scientific += 3 if re.search(r"confidence interval|\bci\b|uncertainty|calibration|risk of bias", t) else 0
    scientific += 3 if re.search(r"panel|\([a-d]\)|left|right|top|bottom|from left", t) else 0
    scientific += 2 if len(caption) >= 100 else 0
    scientific += 3 if category in {"risk_of_bias_reporting", "evidence_map", "heatmap_matrix", "temporal_trend", "forest_meta"} else 0
    scientific = min(25.0, scientific)

    relevant_categories = {
        "risk_of_bias_reporting": 10,
        "evidence_map": 9,
        "temporal_trend": 9,
        "heatmap_matrix": 9,
        "distribution_comparison": 8,
        "workflow_pipeline": 7,
        "study_flow": 6,
        "forest_meta": 6,
        "explainability": 4,
        "model_performance": 3,
        "other": 2,
    }
    relevance = float(relevant_categories[category])
    if re.search(r"systematic|scoping|review|included studies|reporting|methodolog", t):
        relevance = min(10.0, relevance + 1)
    return scientific, relevance


def choose_band(page: fitz.Page, cap: fitz.Rect) -> fitz.Rect:
    """Choose the likely column containing a caption."""
    w, h = page.rect.width, page.rect.height
    margin = max(24.0, w * 0.055)
    if cap.width >= 0.58 * w or (0.37 * w < cap.x0 and cap.x1 < 0.63 * w):
        return fitz.Rect(margin, max(28.0, h * 0.04), w - margin, h - max(28.0, h * 0.04))
    mid = w / 2
    gutter = max(8.0, w * 0.015)
    if cap.x1 <= mid + 0.08 * w:
        return fitz.Rect(margin, max(28.0, h * 0.04), mid - gutter, h - max(28.0, h * 0.04))
    return fitz.Rect(mid + gutter, max(28.0, h * 0.04), w - margin, h - max(28.0, h * 0.04))


def probable_figure_rect(page: fitz.Page, cap: fitz.Rect, other_caps: list[fitz.Rect]) -> tuple[fitz.Rect, str]:
    """Return a generous figure+caption rectangle and a confidence label."""
    band = choose_band(page, cap)
    candidates: list[tuple[float, fitz.Rect, str]] = []

    # Raster/image blocks are the strongest location signal.
    for block in page.get_text("blocks"):
        if int(block[6]) != 1:
            continue
        r = fitz.Rect(block[:4])
        overlap = max(0.0, min(r.x1, band.x1) - max(r.x0, band.x0)) / max(1.0, min(r.width, band.width))
        if r.y1 <= cap.y1 + 12 and overlap > 0.45 and r.get_area() > page.rect.get_area() * 0.015:
            distance = max(0.0, cap.y0 - r.y1)
            candidates.append((r.get_area() / (1 + distance), r, "image"))

    # Vector figures often appear as a substantial drawing cluster.
    try:
        clusters = page.cluster_drawings()
    except Exception:
        clusters = []
    for rr in clusters:
        r = fitz.Rect(rr)
        overlap = max(0.0, min(r.x1, band.x1) - max(r.x0, band.x0)) / max(1.0, min(r.width, band.width))
        if r.y1 <= cap.y1 + 12 and overlap > 0.45 and r.get_area() > page.rect.get_area() * 0.012:
            distance = max(0.0, cap.y0 - r.y1)
            candidates.append((r.get_area() / (1 + distance), r, "vector"))

    if candidates:
        _, art, kind = max(candidates, key=lambda x: x[0])
        x0 = max(band.x0, art.x0 - 8)
        x1 = min(band.x1, art.x1 + 8)
        y0 = max(band.y0, art.y0 - 8)
        y1 = min(page.rect.height - 20, cap.y1 + 5)
        return fitz.Rect(x0, y0, x1, y1), "high" if kind == "image" else "medium"

    # Fallback: preserve enough context to avoid cutting off multi-panel/vector art.
    prior = [r.y1 for r in other_caps if r.y1 < cap.y0 and r.x0 < band.x1 and r.x1 > band.x0]
    lower_bound = max(prior, default=band.y0)
    depth = min(page.rect.height * 0.55, 430.0)
    y0 = max(lower_bound + (5 if prior else 0), cap.y0 - depth, band.y0)
    return fitz.Rect(band.x0, y0, band.x1, min(page.rect.height - 20, cap.y1 + 5)), "context"


def visual_scores(image: Image.Image, crop_rect: fitz.Rect, page: fitz.Page, confidence: str) -> tuple[float, float, float, dict]:
    """Return readability (25), information design (25), production (15), diagnostics."""
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    grey = np.asarray(image.convert("L"), dtype=np.uint8)
    # Ink/contrast and edge density are deliberately broad proxies.
    ink = float(np.mean(grey < 242))
    contrast = float(np.std(grey))
    dx = np.abs(np.diff(grey.astype(np.int16), axis=1))
    dy = np.abs(np.diff(grey.astype(np.int16), axis=0))
    edges = float((np.mean(dx > 22) + np.mean(dy > 22)) / 2)
    q = (rgb // 32).reshape(-1, 3)
    color_bins = int(len(np.unique(q[:: max(1, len(q) // 50000)], axis=0)))
    colorfulness = float(np.mean(np.max(rgb, axis=2) - np.min(rgb, axis=2)))

    min_dim = min(image.size)
    resolution = min(10.0, 10.0 * min_dim / 850.0)
    density = 5.0 * max(0.0, 1.0 - abs(ink - 0.18) / 0.22)
    contrast_score = min(5.0, contrast / 10.0)
    extraction = {"high": 5.0, "medium": 4.0, "context": 2.5}[confidence]
    readability = min(25.0, resolution + density + contrast_score + extraction)

    hierarchy = min(8.0, 2.0 + contrast / 9.0)
    structured_marks = min(9.0, 2.0 + edges * 90.0)
    balanced_density = 5.0 * max(0.0, 1.0 - abs(ink - 0.20) / 0.25)
    restrained_color = 3.0 if colorfulness < 45 else 2.0 if colorfulness < 75 else 1.0
    design = min(25.0, hierarchy + structured_marks + balanced_density + restrained_color)

    vector_like = 1.0 if confidence == "medium" else 0.0
    aspect = crop_rect.width / max(1.0, crop_rect.height)
    aspect_score = 4.0 if 0.65 <= aspect <= 2.3 else 2.5
    production = min(15.0, 5.0 + 3.0 * vector_like + aspect_score + min(3.0, color_bins / 80.0))
    return readability, design, production, {
        "ink_fraction": round(ink, 4),
        "contrast_sd": round(contrast, 2),
        "edge_fraction": round(edges, 4),
        "colorfulness": round(colorfulness, 2),
    }


def make_contact_sheet(rows: list[dict], output: Path, count: int = 40) -> None:
    selected = rows[:count]
    tile_w, tile_h = 520, 390
    sheet = Image.new("RGB", (tile_w * 2, tile_h * math.ceil(len(selected) / 2)), "#d8d8d8")
    draw = ImageDraw.Draw(sheet)
    for i, row in enumerate(selected):
        tile = Image.new("RGB", (tile_w, tile_h), "white")
        im = Image.open(row["image_path"]).convert("RGB")
        im.thumbnail((tile_w - 24, tile_h - 84))
        tile.paste(im, ((tile_w - im.width) // 2, 48))
        td = ImageDraw.Draw(tile)
        title = f"#{i+1}  {row['reference_score']:.1f}  {row['manuscript']} p.{row['page']} {row['figure']}"
        td.text((10, 8), title[:82], fill="black")
        td.text((10, 27), f"{row['category']} | quality {row['quality_score']:.1f} | {row['confidence']}", fill="#444444")
        sheet.paste(tile, ((i % 2) * tile_w, (i // 2) * tile_h))
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=90)


def extract(source: Path, output: Path, dpi: int) -> list[dict]:
    image_root = output / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    failures: list[tuple[str, str]] = []
    pdfs = sorted(source.glob("*.pdf"))
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)

    for index, pdf in enumerate(pdfs, 1):
        try:
            doc = fitz.open(pdf)
            paper_candidates: list[dict] = []
            for page_index, page in enumerate(doc):
                blocks = page.get_text("blocks", sort=True)
                matches = []
                for b in blocks:
                    text = clean_text(b[4])
                    m = CAPTION_RE.match(text)
                    if m:
                        matches.append((m.group("number").lower(), text, fitz.Rect(b[:4])))
                cap_rects = [m[2] for m in matches]
                for number, caption, cap_rect in matches:
                    crop, confidence = probable_figure_rect(page, cap_rect, cap_rects)
                    paper_candidates.append({
                        "number": number,
                        "caption": caption,
                        "page_index": page_index,
                        "crop": crop,
                        "confidence": confidence,
                    })

            # Mentions such as "Fig. 2 shows ..." are commonly duplicated later.
            # Keep the richest candidate per figure number, preferring earlier pages.
            best: dict[str, dict] = {}
            for item in paper_candidates:
                key = item["number"]
                current = best.get(key)
                signal = len(item["caption"]) + 35 * (item["confidence"] != "context")
                if current is None or signal > current["signal"]:
                    item["signal"] = signal
                    best[key] = item

            paper_out = image_root / pdf.stem
            paper_out.mkdir(exist_ok=True)
            for number, item in sorted(best.items(), key=lambda kv: (kv[1]["page_index"], kv[0])):
                page = doc[item["page_index"]]
                pix = page.get_pixmap(matrix=matrix, clip=item["crop"], alpha=False, colorspace=fitz.csRGB)
                image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                image = ImageOps.expand(image, border=2, fill="white")
                out_path = paper_out / f"fig_{number}_p{item['page_index']+1}.jpg"
                image.save(out_path, quality=91, optimize=True, progressive=True)

                category = figure_category(item["caption"])
                scientific, relevance = semantic_scores(item["caption"], category)
                readability, design, production, diagnostics = visual_scores(
                    image, item["crop"], page, item["confidence"]
                )
                quality = readability + design + scientific + production  # /90
                quality_100 = 100.0 * quality / 90.0
                reference_score = 0.90 * quality_100 + relevance
                rows.append({
                    "manuscript": pdf.stem,
                    "pdf_path": str(pdf.relative_to(ROOT)),
                    "page": item["page_index"] + 1,
                    "figure": number,
                    "caption": item["caption"],
                    "category": category,
                    "confidence": item["confidence"],
                    "readability_25": round(readability, 2),
                    "information_design_25": round(design, 2),
                    "scientific_communication_25": round(scientific, 2),
                    "technical_production_15": round(production, 2),
                    "quality_score": round(quality_100, 2),
                    "review_relevance_10": round(relevance, 2),
                    "reference_score": round(reference_score, 2),
                    "width_px": image.width,
                    "height_px": image.height,
                    **diagnostics,
                    "image_path": str(out_path),
                })
            doc.close()
        except Exception as exc:
            failures.append((str(pdf), repr(exc)))
        if index % 50 == 0:
            print(f"processed {index}/{len(pdfs)} PDFs; extracted {len(rows)} figures", flush=True)

    rows.sort(key=lambda r: (-r["reference_score"], -r["quality_score"], r["manuscript"], r["page"]))
    output.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with (output / "figure_catalog.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    with (output / "extraction_failures.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["pdf_path", "error"])
        writer.writerows(failures)
    extracted_papers = {r["manuscript"] for r in rows}
    no_caption = [p for p in pdfs if p.stem not in extracted_papers]
    with (output / "no_numbered_caption_pdfs.tsv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["pdf_path", "status"])
        for pdf in no_caption:
            writer.writerow([str(pdf.relative_to(ROOT)), "no machine-recoverable numbered caption"])
    make_contact_sheet(rows, output / "top40_contact_sheet.jpg", 40)

    category_counts = Counter(r["category"] for r in rows)
    confidence_counts = Counter(r["confidence"] for r in rows)
    scores = [r["quality_score"] for r in rows]
    with (output / "README.md").open("w", encoding="utf-8") as f:
        f.write("# Reference figure audit\n\n")
        f.write(f"Source: `{source.relative_to(ROOT)}` ({len(pdfs)} PDFs). ")
        f.write(f"Extracted: {len(rows)} numbered figures; failures: {len(failures)}; ")
        f.write(f"PDFs without a machine-recoverable numbered caption: {len(no_caption)}.\n\n")
        f.write("## Ranking rubric\n\n")
        f.write("Quality is scored on readability (25), information design (25), scientific communication (25), and technical production (15), rescaled to 100. Review relevance (10) is then added to 90% of that quality score to form the reference score (100). Automated visual proxies are used for the exhaustive first pass; the shortlist requires human visual review. Extraction confidence is reported separately and is never treated as original-figure quality.\n\n")
        if scores:
            f.write(f"Quality score median {statistics.median(scores):.1f}; range {min(scores):.1f}–{max(scores):.1f}.\n\n")
        f.write("## Categories\n\n")
        for key, value in category_counts.most_common():
            f.write(f"- {key}: {value}\n")
        f.write("\n## Extraction confidence\n\n")
        for key, value in confidence_counts.most_common():
            f.write(f"- {key}: {value}\n")
        f.write("\n## Top 30 candidates\n\n")
        f.write("|Rank|Score|Paper|Figure|Category|Caption|\n|---:|---:|---|---|---|---|\n")
        for i, r in enumerate(rows[:30], 1):
            cap = r["caption"].replace("|", "\\|")[:180]
            rel_image = Path(r["image_path"]).relative_to(output)
            f.write(f"|{i}|{r['reference_score']:.1f}|{r['manuscript']}|[Fig {r['figure']}]({rel_image.as_posix()})|{r['category']}|{cap}|\n")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dpi", type=int, default=150)
    args = parser.parse_args()
    rows = extract(args.source.resolve(), args.output.resolve(), args.dpi)
    print(f"done: {len(rows)} figures -> {args.output}")


if __name__ == "__main__":
    main()

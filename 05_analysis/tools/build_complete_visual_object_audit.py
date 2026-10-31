#!/usr/bin/env python3
"""Inventory every figure/table in the 222 included full reports and their supplements.

This script deliberately does *not* run a third-party OCR engine.  It performs the
reproducible mechanical stage only: locate objects, preserve native text and table
cells, render image crops, reconcile caption labels, and create a queue for ChatGPT
vision review.  Vision annotations are stored separately and merged on rerun.

Outputs
-------
data/visual_object_audit/objects/<study>/       rendered objects and exact tables
data/visual_object_audit/contact_sheets/        one or more sheets per study
data/visual_object_audit/vision_annotations/    ChatGPT-written JSON annotations
data/ALL_REPORT_VISUAL_OBJECTS.tsv              one row per object
data/ALL_REPORT_VISUAL_COVERAGE.tsv             one row per included study
data/CHATGPT_VISION_REVIEW_QUEUE.tsv             image-AI work queue
data/ALL_REPORT_VISUAL_AUDIT.md                 coverage report
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

import fitz
import openpyxl
from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "INTEGRATED_STUDY_AUDIT.tsv"
OUT = ROOT / "data" / "visual_object_audit"
OBJECT_TSV = ROOT / "data" / "ALL_REPORT_VISUAL_OBJECTS.tsv"
COVERAGE_TSV = ROOT / "data" / "ALL_REPORT_VISUAL_COVERAGE.tsv"
QUEUE_TSV = ROOT / "data" / "CHATGPT_VISION_REVIEW_QUEUE.tsv"
REPORT_MD = ROOT / "data" / "ALL_REPORT_VISUAL_AUDIT.md"

CAPTION_RE = re.compile(
    r"^\s*[\[<]?\s*(?P<prefix>(?:supplement(?:ary|al)\s+)?(?:figure|fig\.?|table)|efigure|etable|그림|표)\s*"
    r"(?P<number>S?\d+(?:[.\-]\d+)*(?:[A-Za-z])?|[IVXLC]+)\s*[\]>]?\s*(?:[.:)]|\s|$)\s*(?P<body>.*)",
    re.I,
)
METRIC_RE = re.compile(
    r"(?i)\b(?:AUROC|AUC|AUPRC|accuracy|balanced accuracy|F1(?:[- ]score)?|precision|recall|"
    r"sensitivity|specificity|NPV|PPV|MCC|Brier(?: score)?|calibration|odds ratio|OR|"
    r"confidence interval|CI|p[- ]?value|SHAP)\b.{0,55}?(?:[-+]?\d+(?:\.\d+)?%?)"
)
IGNORE_SUPP = {"manifest.tsv", "study_status.tsv"}
SUPPORTED = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".mp4", ".zip"}

# A small number of PDFs render captions as vector outlines, so neither the
# caption nor its label exists in the native PDF text layer.  These hints are
# based on direct page inspection and keep those objects in the same auditable
# extraction path as normally labelled objects.
MANUAL_PDF_OBJECT_HINTS = {
    "ibrahum2023extreme": {
        ("figure", "1"): 2,
        ("table", "1"): 4,
        ("table", "2"): 5,
        ("figure", "2"): 6,
        ("figure", "3"): 6,
    },
    # Turkish captions in this thesis are page-image/vector content and are
    # absent from the native text layer. Pages 9–10 list the objects; the page
    # locations below were independently confirmed from full-page vision review.
    "ozcan2024artificial": {
        ("table", "1.1"): 14,
        ("figure", "1.1"): 15,
        ("table", "2.1"): 19,
        ("table", "2.1_CONT"): 20,
        ("figure", "2.1"): 22,
        ("figure", "2.2"): 24,
        ("figure", "2.3"): 25,
        ("table", "2.2"): 25,
        ("figure", "2.4"): 26,
        ("figure", "2.5"): 28,
        ("figure", "2.6"): 28,
        ("figure", "2.7"): 29,
        ("figure", "2.8"): 30,
        ("figure", "2.9"): 30,
        ("figure", "3.1"): 31,
        ("figure", "3.2"): 32,
    },
}


def clean(value: object, limit: int | None = None) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] if limit else text


def safe(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return value[:110] or "object"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def kind_from_prefix(prefix: str) -> str:
    return "table" if re.search(r"table|^표$", prefix, re.I) else "figure"


def canonical_label(kind: str, number: str) -> str:
    return f"{kind}:{number.upper().replace(' ', '')}"


def caption_matches(text: str) -> list[re.Match[str]]:
    found = []
    for line in text.splitlines():
        m = CAPTION_RE.match(line)
        if m and len(clean(m.group("body"))) >= 2:
            found.append(m)
    return found


def content_domains(text: str) -> str:
    rules = {
        "study flow/workflow": r"flow|workflow|pipeline|participant|inclusion|exclusion",
        "model performance": r"auc|auroc|accuracy|precision|recall|sensitivity|specificity|f1|calibration|confusion",
        "feature importance/explainability": r"shap|feature importance|variable importance|lime|permutation",
        "sample characteristics": r"characteristic|demographic|baseline|sample|population",
        "association/inference": r"odds ratio|confidence interval|regression|p.?value|association",
        "distribution/comparison": r"distribution|prevalence|frequency|comparison|difference",
        "model architecture": r"architecture|network|layer|encoder|decoder|transformer|cnn|lstm",
        "data processing": r"preprocess|imput|normaliz|standardiz|sampling|smote|split|cross.?validation",
    }
    low = text.lower()
    return "; ".join(name for name, pat in rules.items() if re.search(pat, low)) or "other/unspecified"


def native_interpretation(kind: str, label: str, caption: str, native: str, table_rows: list[list[str]] | None) -> str:
    basis = clean(caption, 900)
    facts = list(dict.fromkeys(clean(x) for x in METRIC_RE.findall(caption + " " + native)))
    # findall returns only the named metric with this regex; preserve richer matching spans instead
    facts = [clean(m.group(0), 120) for m in METRIC_RE.finditer(caption + " " + native)][:20]
    if kind == "table" and table_rows:
        width = max((len(r) for r in table_rows), default=0)
        header = " | ".join(clean(x, 100) for x in table_rows[0]) if table_rows else ""
        result = f"{label} is a structured table with {len(table_rows)} extracted rows and up to {width} columns."
        if basis:
            result += f" Caption: {basis}"
        if header:
            result += f" Header/first row: {header}."
    else:
        result = f"{label} is a {kind}."
        if basis:
            result += f" Caption: {basis}"
        result += " Image-specific labels, values, trends, and panel relationships require ChatGPT vision review."
    if facts:
        result += " Native-text quantitative signals: " + "; ".join(facts) + "."
    return result


def annotation_for(object_id: str) -> dict:
    p = OUT / "vision_annotations" / f"{object_id}.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "invalid_annotation_json"}


def base_row(key: str, source_scope: str, source_path: str, source_sha: str, source_format: str) -> dict:
    return {
        "study_key": key,
        "source_scope": source_scope,
        "source_path": source_path,
        "source_sha256": source_sha,
        "source_format": source_format,
        "object_id": "",
        "object_type": "",
        "object_label": "",
        "object_number": "",
        "page_or_sheet": "",
        "caption": "",
        "nearby_context": "",
        "native_text": "",
        "structured_table_path": "",
        "image_path": "",
        "image_width_px": "",
        "image_height_px": "",
        "extraction_method": "",
        "extraction_confidence": "",
        "content_domains": "",
        "native_interpretation": "",
        "vision_required": "",
        "chatgpt_vision_status": "",
        "chatgpt_review_stage": "",
        "chatgpt_visible_text": "",
        "chatgpt_interpretation": "",
        "chatgpt_key_values": "",
        "chatgpt_uncertainty": "",
        "manual_review_reason": "",
    }


def save_image(image: Image.Image, key: str, object_id: str) -> tuple[str, int, int]:
    target = OUT / "objects" / key / f"{object_id}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.save(target, format="PNG", optimize=True)
    return rel(target), image.width, image.height


def decode_office_image(data: bytes, member: str) -> Image.Image:
    """Decode raster or vector OOXML media without OCR."""
    try:
        return Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        pass
    suffix = Path(member).suffix.lower().lstrip(".")
    try:
        doc = fitz.open(stream=data, filetype=suffix)
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False, colorspace=fitz.csRGB)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()
        return image
    except Exception:
        pass
    with tempfile.TemporaryDirectory(prefix="office_media_") as td:
        tmp = Path(td)
        source = tmp / Path(member).name
        source.write_bytes(data)
        subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp), str(source)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False)
        pdf = tmp / (source.stem + ".pdf")
        if not pdf.exists():
            raise OSError(f"cannot decode OOXML media {member}")
        doc = fitz.open(pdf)
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False, colorspace=fitz.csRGB)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        doc.close()
        return image


def save_table(rows: list[list[str]], key: str, object_id: str) -> str:
    target = OUT / "objects" / key / f"{object_id}.tsv"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerows(rows)
    return rel(target)


def page_band(page: fitz.Page, cap: fitz.Rect) -> fitz.Rect:
    w, h = page.rect.width, page.rect.height
    margin = max(20.0, w * .035)
    if cap.width > .58 * w:
        return fitz.Rect(margin, 25, w - margin, h - 20)
    mid = w / 2
    if cap.x1 < mid + .06 * w:
        return fitz.Rect(margin, 25, mid - 5, h - 20)
    return fitz.Rect(mid + 5, 25, w - margin, h - 20)


def overlap_fraction(a: fitz.Rect, b: fitz.Rect) -> float:
    inter = a & b
    return max(0.0, inter.get_area()) / max(1.0, min(a.get_area(), b.get_area()))


def figure_crop(page: fitz.Page, cap: fitz.Rect) -> tuple[fitz.Rect, str, bool]:
    band = page_band(page, cap)
    candidates: list[tuple[float, fitz.Rect, str]] = []
    raster = False
    for block in page.get_text("blocks"):
        if int(block[6]) != 1:
            continue
        r = fitz.Rect(block[:4])
        if overlap_fraction(r, band) < .25 or r.get_area() < page.rect.get_area() * .008:
            continue
        distance = min(abs(cap.y0 - r.y1), abs(r.y0 - cap.y1))
        if distance < page.rect.height * .55:
            candidates.append((r.get_area() / (1 + distance), r, "raster"))
    try:
        clusters = page.cluster_drawings()
    except Exception:
        clusters = []
    for rr in clusters:
        r = fitz.Rect(rr)
        if overlap_fraction(r, band) < .25 or r.get_area() < page.rect.get_area() * .008:
            continue
        distance = min(abs(cap.y0 - r.y1), abs(r.y0 - cap.y1))
        if distance < page.rect.height * .55:
            candidates.append((r.get_area() / (1 + distance), r, "vector"))
    if candidates:
        _, art, mode = max(candidates, key=lambda x: x[0])
        raster = mode == "raster"
        union = art | cap
        crop = fitz.Rect(max(band.x0, union.x0 - 7), max(20, union.y0 - 7),
                         min(band.x1, union.x1 + 7), min(page.rect.height - 15, union.y1 + 7))
        return crop, f"caption-linked {mode} region", raster
    # Most captions are below figures; retain a generous column crop for vector art.
    if cap.y0 > page.rect.height * .38:
        crop = fitz.Rect(band.x0, max(band.y0, cap.y0 - min(430, page.rect.height * .58)), band.x1, min(band.y1, cap.y1 + 5))
    else:
        crop = fitz.Rect(band.x0, max(band.y0, cap.y0 - 20), band.x1, min(band.y1, cap.y1 + min(430, page.rect.height * .58)))
    return crop, "caption-context fallback", False


def table_crop(page: fitz.Page, cap: fitz.Rect) -> tuple[fitz.Rect, list[list[str]], str]:
    band = page_band(page, cap)
    found = []
    try:
        found = list(page.find_tables().tables)
    except Exception:
        pass
    scored = []
    for table in found:
        r = fitz.Rect(table.bbox)
        if overlap_fraction(r, band) < .2:
            continue
        distance = min(abs(cap.y0 - r.y1), abs(r.y0 - cap.y1))
        scored.append((distance, -r.get_area(), table, r))
    if scored:
        _, _, table, r = min(scored, key=lambda x: (x[0], x[1]))
        try:
            values = [[clean(c) for c in row] for row in table.extract()]
        except Exception:
            values = []
        union = r | cap
        crop = fitz.Rect(max(band.x0, union.x0 - 5), max(15, union.y0 - 5),
                         min(band.x1, union.x1 + 5), min(page.rect.height - 12, union.y1 + 5))
        return crop, values, "caption-linked PyMuPDF table"
    # Caption is normally above a table.
    crop = fitz.Rect(band.x0, max(15, cap.y0 - 5), band.x1, min(band.y1, cap.y1 + min(470, page.rect.height * .62)))
    return crop, [], "caption-context table fallback"


def render(page: fitz.Page, crop: fitz.Rect, dpi: int) -> Image.Image:
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), clip=crop, alpha=False, colorspace=fitz.csRGB)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def process_pdf(path: Path, key: str, scope: str, source_label: str, dpi: int, seq_start: int) -> tuple[list[dict], set[str], list[str], int]:
    rows: list[dict] = []
    expected: set[str] = set()
    errors: list[str] = []
    seq = seq_start
    digest = sha256(path)
    try:
        doc = fitz.open(path)
    except Exception as exc:
        return rows, expected, [f"{source_label}:open:{type(exc).__name__}"], seq
    seen: set[str] = set()
    manual_hints = MANUAL_PDF_OBJECT_HINTS.get(key, {}) if scope == "main" else {}
    for kind_number in manual_hints:
        expected.add(f"{source_label}|{canonical_label(*kind_number)}")
    try:
        for page_no, page in enumerate(doc, 1):
            page_text = page.get_text("text", sort=True)
            for m in caption_matches(page_text):
                if kind_from_prefix(m.group("prefix")) == "figure" and re.match(
                        r"(?i)(?:shows?|presents?|illustrates?|depicts?)\b", clean(m.group("body"))):
                    continue
                expected.add(f"{source_label}|{canonical_label(kind_from_prefix(m.group('prefix')), m.group('number'))}")
            blocks = page.get_text("blocks", sort=True)
            candidates = []
            for index, block in enumerate(blocks):
                if int(block[6]) == 1:
                    continue
                btext = str(block[4])
                matches = caption_matches(btext)
                for m in matches:
                    kind = kind_from_prefix(m.group("prefix"))
                    number = m.group("number")
                    # Prose references such as "Figure 4 shows ..." are not
                    # captions. Accepting them can hide the real object later in
                    # the report because labels are deduplicated by number.
                    if kind == "figure" and re.match(r"(?i)(?:shows?|presents?|illustrates?|depicts?)\b", clean(m.group("body"))):
                        continue
                    label = canonical_label(kind, number)
                    candidates.append((kind, number, label, clean(m.group(0)), fitz.Rect(block[:4]), index))
            # Keep one caption instance per labelled object in a source, preferring the first.
            for kind, number, label, caption, cap, index in candidates:
                source_object_key = f"{source_label}|{label}"
                if source_object_key in seen:
                    continue
                seen.add(source_object_key)
                seq += 1
                object_id = f"{safe(key)}__{seq:04d}__{kind}_{safe(number)}"
                table_rows: list[list[str]] = []
                if kind == "table":
                    crop, table_rows, method = table_crop(page, cap)
                    raster = any(int(b[6]) == 1 and overlap_fraction(fitz.Rect(b[:4]), crop) > .15 for b in blocks)
                else:
                    crop, method, raster = figure_crop(page, cap)
                # PyMuPDF text coordinates in rotated landscape PDFs can extend beyond
                # Page.rect, while pixmap clipping uses the displayed rectangle.  A
                # full displayed-page crop is safer than silently producing a blank
                # object; the caption still identifies the object unambiguously.
                if page.rotation in {90, 270}:
                    crop = page.rect
                    method += "; rotated full-page preservation"
                try:
                    image = render(page, crop, dpi)
                    image_path, iw, ih = save_image(image, key, object_id)
                except Exception as exc:
                    image_path, iw, ih = "", "", ""
                    errors.append(f"{source_label}:p{page_no}:{label}:render:{type(exc).__name__}")
                native = clean(page.get_text("text", sort=True) if page.rotation in {90, 270}
                               else page.get_text("text", clip=crop, sort=True), 12000)
                context_parts = []
                for j in range(max(0, index - 1), min(len(blocks), index + 2)):
                    if int(blocks[j][6]) != 1:
                        context_parts.append(str(blocks[j][4]))
                context = clean(" ".join(context_parts), 4000)
                table_path = save_table(table_rows, key, object_id) if table_rows else ""
                row = base_row(key, scope, source_label, digest, ".pdf")
                row.update({
                    "object_id": object_id, "object_type": kind, "object_label": label,
                    "object_number": number, "page_or_sheet": str(page_no), "caption": caption,
                    "nearby_context": context, "native_text": native,
                    "structured_table_path": table_path, "image_path": image_path,
                    "image_width_px": iw, "image_height_px": ih,
                    "extraction_method": method, "extraction_confidence": "high" if table_rows or "linked" in method else "context",
                    "content_domains": content_domains(caption + " " + native),
                    "native_interpretation": native_interpretation(kind, label, caption, native, table_rows),
                    "vision_required": "Y" if kind == "figure" or raster or not table_rows else "N",
                    "chatgpt_vision_status": "pending" if kind == "figure" or raster or not table_rows else "not_required_native_table",
                    "manual_review_reason": "ChatGPT vision interpretation required" if kind == "figure" or raster or not table_rows else "",
                })
                ann = annotation_for(object_id)
                if ann:
                    row.update({
                        "chatgpt_vision_status": ann.get("status", "completed"),
                        "chatgpt_review_stage": ann.get("review_stage", "first_pass"),
                        "chatgpt_visible_text": ann.get("visible_text", ""),
                        "chatgpt_interpretation": ann.get("interpretation", ""),
                        "chatgpt_key_values": json.dumps(ann.get("key_values", []), ensure_ascii=False),
                        "chatgpt_uncertainty": ann.get("uncertainty", ""),
                        "manual_review_reason": ann.get("manual_review_reason", ""),
                    })
                rows.append(row)

        # Reconcile labels that are recoverable from the page text but were not
        # isolated as stand-alone caption blocks (common in older two-column PDFs).
        existing = {f"{source_label}|{r['object_label']}" for r in rows}
        for expected_item in sorted(expected - existing):
            label = expected_item.removeprefix(source_label + "|")
            kind, number = label.split(":", 1)
            number_pat = re.escape(number).replace(r"\-", r"[-–]")
            mention = re.compile(
                rf"(?i)(?:supplement(?:ary|al)\s+)?(?:fig(?:ure)?\.?|table|efigure|etable|그림|표)\s*{number_pat}\b"
            )
            hinted_page = manual_hints.get((kind, number))
            page_candidates = []
            if hinted_page and 1 <= hinted_page <= len(doc):
                page = doc[hinted_page - 1]
                ptext = page.get_text("text", sort=True)
                # A direct visual inspection hint outranks text-layer matches;
                # the latter may only be an in-text citation on another page.
                page_candidates.append((10_000, hinted_page, page, ptext))
            for page_no, page in enumerate(doc, 1):
                ptext = page.get_text("text", sort=True)
                hits = list(mention.finditer(ptext))
                if not hits:
                    continue
                visual_signal = len(page.get_images(full=True))
                try:
                    visual_signal += min(8, len(page.cluster_drawings()))
                except Exception:
                    pass
                score = 20 * len(hits) + 3 * visual_signal
                if re.search(rf"(?i)(?:figure|fig\.?|table)\s*{number_pat}\s*[.:]", ptext):
                    score += 30
                page_candidates.append((score, page_no, page, ptext))
            if not page_candidates:
                continue
            _, page_no, page, ptext = max(page_candidates, key=lambda x: x[0])
            seq += 1
            object_id = f"{safe(key)}__{seq:04d}__{kind}_{safe(number)}_recovered"
            try:
                image = render(page, page.rect, dpi)
                image_path, iw, ih = save_image(image, key, object_id)
            except Exception as exc:
                image_path, iw, ih = "", "", ""
                errors.append(f"{source_label}:p{page_no}:{label}:recovery-render:{type(exc).__name__}")
            hit = mention.search(ptext)
            context = clean(ptext[max(0, hit.start() - 500):hit.end() + 1400] if hit else ptext, 4000)
            row = base_row(key, scope, source_label, digest, ".pdf")
            row.update({
                "object_id": object_id, "object_type": kind, "object_label": label,
                "object_number": number, "page_or_sheet": str(page_no), "caption": context,
                "nearby_context": context, "native_text": clean(ptext, 12000),
                "image_path": image_path, "image_width_px": iw, "image_height_px": ih,
                "extraction_method": "caption-reconciliation full-page recovery",
                "extraction_confidence": "reconciliation_candidate",
                "content_domains": content_domains(context + " " + ptext),
                "native_interpretation": native_interpretation(kind, label, context, ptext, None),
                "vision_required": "Y", "chatgpt_vision_status": "pending",
                "manual_review_reason": "ChatGPT vision must confirm the recovered full-page object and distinguish caption from in-text mention",
            })
            ann = annotation_for(object_id)
            if ann:
                row.update({"chatgpt_vision_status": ann.get("status", "completed"),
                            "chatgpt_review_stage": ann.get("review_stage", "first_pass"),
                            "chatgpt_visible_text": ann.get("visible_text", ""),
                            "chatgpt_interpretation": ann.get("interpretation", ""),
                            "chatgpt_key_values": json.dumps(ann.get("key_values", []), ensure_ascii=False),
                            "chatgpt_uncertainty": ann.get("uncertainty", ""),
                            "manual_review_reason": ann.get("manual_review_reason", "")})
            rows.append(row)
    except Exception as exc:
        errors.append(f"{source_label}:scan:{type(exc).__name__}:{clean(exc, 180)}")
    finally:
        doc.close()
    return rows, expected, errors, seq


def xml_text(node: ET.Element) -> str:
    vals = []
    for e in node.iter():
        tag = e.tag.rsplit("}", 1)[-1]
        if tag in {"t", "instrText", "delText"} and e.text:
            vals.append(e.text)
        elif tag in {"br", "tab"}:
            vals.append(" ")
    return clean(" ".join(vals))


def process_docx(path: Path, key: str, scope: str, source_label: str, seq_start: int) -> tuple[list[dict], set[str], list[str], int]:
    rows, errors, expected = [], [], set()
    seq = seq_start
    digest = sha256(path)
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
            rels = {}
            rel_name = "word/_rels/document.xml.rels"
            if rel_name in z.namelist():
                rr = ET.fromstring(z.read(rel_name))
                for item in rr:
                    rels[item.attrib.get("Id", "")] = item.attrib.get("Target", "")
            body = next((x for x in root.iter() if x.tag.rsplit("}", 1)[-1] == "body"), root)
            items = []
            for node in list(body):
                tag = node.tag.rsplit("}", 1)[-1]
                text = xml_text(node)
                embeds = [e.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed", "")
                          for e in node.iter() if e.tag.rsplit("}", 1)[-1] == "blip"]
                items.append((tag, node, text, [e for e in embeds if e]))
                for m in caption_matches(text):
                    expected.add(f"{source_label}|{canonical_label(kind_from_prefix(m.group('prefix')), m.group('number'))}")

            image_occurrences = []
            for idx, (tag, node, text, embeds) in enumerate(items):
                for rid in embeds:
                    image_occurrences.append((idx, rid))
            used_media = set()
            for idx, rid in image_occurrences:
                target = rels.get(rid, "")
                member = "word/" + target.lstrip("/")
                member = str(Path(member))
                if member not in z.namelist():
                    continue
                used_media.add(member)
                nearby = [items[j][2] for j in range(max(0, idx - 2), min(len(items), idx + 3)) if items[j][2]]
                cap = next((t for t in nearby if caption_matches(t)), "")
                m = caption_matches(cap)[0] if cap and caption_matches(cap) else None
                number = m.group("number") if m else f"media{len(used_media)}"
                label = canonical_label("figure", number) if m else f"figure:UNLABELLED_MEDIA_{len(used_media)}"
                seq += 1
                object_id = f"{safe(key)}__{seq:04d}__figure_{safe(number)}"
                try:
                    image = decode_office_image(z.read(member), member)
                    image_path, iw, ih = save_image(image, key, object_id)
                except Exception as exc:
                    image_path, iw, ih = "", "", ""
                    errors.append(f"{source_label}:{member}:image:{type(exc).__name__}")
                row = base_row(key, scope, source_label, digest, ".docx")
                row.update({
                    "object_id": object_id, "object_type": "figure", "object_label": label,
                    "object_number": number, "page_or_sheet": f"docx:{idx+1}", "caption": cap,
                    "nearby_context": clean(" ".join(nearby), 4000), "native_text": "",
                    "image_path": image_path, "image_width_px": iw, "image_height_px": ih,
                    "extraction_method": "OOXML image relationship", "extraction_confidence": "high",
                    "content_domains": content_domains(cap + " " + " ".join(nearby)),
                    "native_interpretation": native_interpretation("figure", label, cap, "", None),
                    "vision_required": "Y", "chatgpt_vision_status": "pending",
                    "manual_review_reason": "ChatGPT vision interpretation required",
                })
                ann = annotation_for(object_id)
                if ann:
                    row.update({"chatgpt_vision_status": ann.get("status", "completed"),
                                "chatgpt_review_stage": ann.get("review_stage", "first_pass"),
                                "chatgpt_visible_text": ann.get("visible_text", ""),
                                "chatgpt_interpretation": ann.get("interpretation", ""),
                                "chatgpt_key_values": json.dumps(ann.get("key_values", []), ensure_ascii=False),
                                "chatgpt_uncertainty": ann.get("uncertainty", ""),
                                "manual_review_reason": ann.get("manual_review_reason", "")})
                rows.append(row)

            table_i = 0
            for idx, (tag, node, text, embeds) in enumerate(items):
                if tag != "tbl":
                    continue
                table_i += 1
                matrix = []
                for tr in (x for x in node if x.tag.rsplit("}", 1)[-1] == "tr"):
                    matrix.append([xml_text(tc) for tc in tr if tc.tag.rsplit("}", 1)[-1] == "tc"])
                nearby = [items[j][2] for j in range(max(0, idx - 2), min(len(items), idx + 3)) if items[j][2]]
                cap = next((t for t in nearby if caption_matches(t) and kind_from_prefix(caption_matches(t)[0].group("prefix")) == "table"), "")
                m = caption_matches(cap)[0] if cap and caption_matches(cap) else None
                number = m.group("number") if m else f"docx{table_i}"
                label = canonical_label("table", number) if m else f"table:UNLABELLED_DOCX_{table_i}"
                seq += 1
                object_id = f"{safe(key)}__{seq:04d}__table_{safe(number)}"
                table_path = save_table(matrix, key, object_id)
                row = base_row(key, scope, source_label, digest, ".docx")
                row.update({
                    "object_id": object_id, "object_type": "table", "object_label": label,
                    "object_number": number, "page_or_sheet": f"docx:{idx+1}", "caption": cap,
                    "nearby_context": clean(" ".join(nearby), 4000), "native_text": clean(text, 12000),
                    "structured_table_path": table_path, "extraction_method": "OOXML table cells",
                    "extraction_confidence": "high", "content_domains": content_domains(cap + " " + text),
                    "native_interpretation": native_interpretation("table", label, cap, text, matrix),
                    "vision_required": "N", "chatgpt_vision_status": "not_required_native_table",
                })
                rows.append(row)
    except Exception as exc:
        errors.append(f"{source_label}:docx:{type(exc).__name__}:{clean(exc, 180)}")
    return rows, expected, errors, seq


def process_workbook(path: Path, key: str, scope: str, source_label: str, seq_start: int) -> tuple[list[dict], set[str], list[str], int]:
    rows, errors, expected = [], [], set()
    seq = seq_start
    digest = sha256(path)
    try:
        wb = openpyxl.load_workbook(path, read_only=False, data_only=True)
        for ws in wb.worksheets:
            matrix = []
            for values in ws.iter_rows(values_only=True):
                row = [clean(x) for x in values]
                while row and row[-1] == "":
                    row.pop()
                if row:
                    matrix.append(row)
            if matrix:
                seq += 1
                number = safe(ws.title)
                object_id = f"{safe(key)}__{seq:04d}__table_sheet_{number}"
                table_path = save_table(matrix, key, object_id)
                row = base_row(key, scope, source_label, digest, path.suffix.lower())
                row.update({
                    "object_id": object_id, "object_type": "table", "object_label": f"table:SHEET_{ws.title}",
                    "object_number": ws.title, "page_or_sheet": ws.title,
                    "caption": f"Spreadsheet sheet: {ws.title}", "native_text": clean(" ".join(" | ".join(r) for r in matrix), 12000),
                    "structured_table_path": table_path, "extraction_method": "spreadsheet cells",
                    "extraction_confidence": "high", "content_domains": content_domains(" ".join(" ".join(r) for r in matrix[:20])),
                    "native_interpretation": native_interpretation("table", f"table:SHEET_{ws.title}", f"Spreadsheet sheet: {ws.title}", "", matrix),
                    "vision_required": "N", "chatgpt_vision_status": "not_required_native_table",
                })
                rows.append(row)
            # Charts and drawings are retained as separate objects even when openpyxl cannot render them.
            for chart_i, chart in enumerate(getattr(ws, "_charts", []), 1):
                seq += 1
                object_id = f"{safe(key)}__{seq:04d}__figure_chart_{safe(ws.title)}_{chart_i}"
                title = clean(getattr(chart, "title", ""), 800)
                row = base_row(key, scope, source_label, digest, path.suffix.lower())
                row.update({
                    "object_id": object_id, "object_type": "figure", "object_label": f"figure:CHART_{ws.title}_{chart_i}",
                    "object_number": f"{ws.title}-{chart_i}", "page_or_sheet": ws.title, "caption": title,
                    "extraction_method": "OOXML chart inventory", "extraction_confidence": "medium",
                    "content_domains": content_domains(title),
                    "native_interpretation": native_interpretation("figure", f"figure:CHART_{ws.title}_{chart_i}", title, "", None),
                    "vision_required": "Y", "chatgpt_vision_status": "source_render_required",
                    "manual_review_reason": "Spreadsheet chart requires office rendering before ChatGPT vision review",
                })
                rows.append(row)
        wb.close()
    except Exception as exc:
        errors.append(f"{source_label}:workbook:{type(exc).__name__}:{clean(exc, 180)}")
    return rows, expected, errors, seq


def process_image(path: Path, key: str, scope: str, source_label: str, seq_start: int) -> tuple[list[dict], set[str], list[str], int]:
    rows, errors, seq = [], [], seq_start + 1
    object_id = f"{safe(key)}__{seq:04d}__figure_media"
    try:
        image = Image.open(path)
        image_path, iw, ih = save_image(image, key, object_id)
    except Exception as exc:
        return rows, set(), [f"{source_label}:image:{type(exc).__name__}"], seq
    row = base_row(key, scope, source_label, sha256(path), path.suffix.lower())
    row.update({
        "object_id": object_id, "object_type": "figure", "object_label": "figure:STANDALONE_MEDIA",
        "object_number": path.stem, "page_or_sheet": "standalone", "caption": path.name,
        "image_path": image_path, "image_width_px": iw, "image_height_px": ih,
        "extraction_method": "standalone supplement image", "extraction_confidence": "high",
        "content_domains": content_domains(path.name),
        "native_interpretation": native_interpretation("figure", "figure:STANDALONE_MEDIA", path.name, "", None),
        "vision_required": "Y", "chatgpt_vision_status": "pending",
        "manual_review_reason": "ChatGPT vision interpretation required",
    })
    ann = annotation_for(object_id)
    if ann:
        row.update({"chatgpt_vision_status": ann.get("status", "completed"),
                    "chatgpt_review_stage": ann.get("review_stage", "first_pass"),
                    "chatgpt_visible_text": ann.get("visible_text", ""),
                    "chatgpt_interpretation": ann.get("interpretation", ""),
                    "chatgpt_key_values": json.dumps(ann.get("key_values", []), ensure_ascii=False),
                    "chatgpt_uncertainty": ann.get("uncertainty", ""),
                    "manual_review_reason": ann.get("manual_review_reason", "")})
    rows.append(row)
    return rows, set(), errors, seq


def process_video(path: Path, key: str, scope: str, source_label: str, seq_start: int) -> tuple[list[dict], set[str], list[str], int]:
    """Preserve representative beginning/middle/end frames for visual review."""
    seq = seq_start + 1
    object_id = f"{safe(key)}__{seq:04d}__figure_video"
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False,
        )
        duration = max(0.1, float(probe.stdout.strip() or 0.1))
        frames = []
        with tempfile.TemporaryDirectory(prefix="video_frames_") as td:
            tmp = Path(td)
            for i, sec in enumerate((0.0, duration * .5, max(0.0, duration - .2))):
                target = tmp / f"frame_{i}.png"
                subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{sec:.3f}", "-i", str(path),
                                "-frames:v", "1", "-y", str(target)], timeout=120, check=False)
                if target.exists():
                    frames.append(Image.open(target).convert("RGB"))
            if not frames:
                raise OSError("no decodable video frames")
            width = max(x.width for x in frames)
            prepared = []
            for frame in frames:
                if frame.width != width:
                    frame.thumbnail((width, frame.height))
                prepared.append(frame)
            sheet = Image.new("RGB", (width, sum(x.height for x in prepared)), "white")
            y = 0
            for frame in prepared:
                sheet.paste(frame, (0, y)); y += frame.height
        image_path, iw, ih = save_image(sheet, key, object_id)
    except Exception as exc:
        return [], set(), [f"{source_label}:video:{type(exc).__name__}:{clean(exc, 160)}"], seq
    row = base_row(key, scope, source_label, sha256(path), path.suffix.lower())
    row.update({
        "object_id": object_id, "object_type": "figure", "object_label": "figure:VIDEO_FRAMES",
        "object_number": path.stem, "page_or_sheet": "start/middle/end frames", "caption": path.name,
        "image_path": image_path, "image_width_px": iw, "image_height_px": ih,
        "extraction_method": "video representative-frame contact sheet", "extraction_confidence": "medium",
        "content_domains": content_domains(path.name),
        "native_interpretation": "Visual supplement represented by beginning, middle, and ending frames; ChatGPT vision review required.",
        "vision_required": "Y", "chatgpt_vision_status": "pending",
        "manual_review_reason": "ChatGPT vision interpretation required; frames do not replace full temporal review",
    })
    ann = annotation_for(object_id)
    if ann:
        row.update({
            "chatgpt_vision_status": ann.get("status", "completed"),
            "chatgpt_review_stage": ann.get("review_stage", "first_pass"),
            "chatgpt_visible_text": ann.get("visible_text", ""),
            "chatgpt_interpretation": ann.get("interpretation", ""),
            "chatgpt_key_values": json.dumps(ann.get("key_values", []), ensure_ascii=False),
            "chatgpt_uncertainty": ann.get("uncertainty", ""),
            "manual_review_reason": ann.get("manual_review_reason", ""),
        })
    return [row], set(), [], seq


def convert_office(path: Path, target: str, tmp: Path) -> Path | None:
    subprocess.run(["libreoffice", "--headless", "--convert-to", target, "--outdir", str(tmp), str(path)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180, check=False)
    candidates = sorted(tmp.glob(path.stem + ".*"), key=lambda p: p.stat().st_mtime)
    return candidates[-1] if candidates else None


def reconcile_unlabelled(rows: list[dict], expected: set[str], source_label: str) -> list[str]:
    """Pair unlabelled OOXML objects with otherwise unmatched captions in document order."""
    existing = {r["object_label"] for r in rows}
    missing = [x.split("|", 1)[1] for x in sorted(expected) if x.startswith(source_label + "|") and x.split("|", 1)[1] not in existing]
    for kind in ("figure", "table"):
        labels = [x for x in missing if x.startswith(kind + ":")]
        candidates = [r for r in rows if r["object_type"] == kind and r["object_label"].startswith(kind + ":UNLABELLED")]
        for row, label in zip(candidates, labels):
            row["object_label"] = label
            row["object_number"] = label.split(":", 1)[1]
            row["extraction_method"] += "; paired to unmatched OOXML caption"
    existing = {r["object_label"] for r in rows}
    return [x for x in missing if x not in existing]


def dispatch(path: Path, key: str, scope: str, source_label: str, dpi: int, seq: int, tmp: Path) -> tuple[list[dict], set[str], list[str], int]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return process_pdf(path, key, scope, source_label, dpi, seq)
    if ext == ".docx":
        rows, expected, errors, seq = process_docx(path, key, scope, source_label, seq)
        reconcile_unlabelled(rows, expected, source_label)
        needs_render = any(r["object_type"] == "figure" for r in rows) or any("|figure:" in x for x in expected)
        if needs_render:
            rendered = convert_office(path, "pdf", tmp)
            if rendered:
                pdf_rows, pdf_expected, pdf_errors, seq = process_pdf(rendered, key, scope, source_label, dpi, seq)
                original_digest = sha256(path)
                expected.update(pdf_expected)
                reconcile_unlabelled(rows, expected, source_label)
                existing = {r["object_label"] for r in rows}
                for row in pdf_rows:
                    if row["object_label"] not in existing and not row["object_label"].startswith(("figure:UNLABELLED", "table:UNLABELLED")):
                        row["source_sha256"] = original_digest
                        row["source_format"] = ".docx-rendered"
                        row["extraction_method"] += "; recovered from office PDF rendering"
                        rows.append(row)
                        existing.add(row["object_label"])
                errors.extend(pdf_errors)
            else:
                errors.append(f"{source_label}:DOCX PDF rendering failed for figure inventory")
        return rows, expected, errors, seq
    if ext == ".doc":
        converted = convert_office(path, "docx", tmp)
        if converted:
            return dispatch(converted, key, scope, source_label + "::converted.docx", dpi, seq, tmp)
        return [], set(), [f"{source_label}:DOC conversion failed"], seq
    if ext == ".xlsx":
        return process_workbook(path, key, scope, source_label, seq)
    if ext == ".xls":
        converted = convert_office(path, "xlsx", tmp)
        if converted:
            return process_workbook(converted, key, scope, source_label + "::converted.xlsx", seq)
        return [], set(), [f"{source_label}:XLS conversion failed"], seq
    if ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        return process_image(path, key, scope, source_label, seq)
    if ext == ".mp4":
        return process_video(path, key, scope, source_label, seq)
    return [], set(), [f"{source_label}:unsupported:{ext or '[none]'}"], seq


def process_supplement(path: Path, key: str, dpi: int, seq: int, tmp: Path) -> tuple[list[dict], set[str], list[str], int]:
    if path.suffix.lower() != ".zip":
        return dispatch(path, key, "supplement", rel(path), dpi, seq, tmp)
    rows, expected, errors = [], set(), []
    archive_dir = tmp / (safe(path.stem) + "_unzipped")
    archive_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                dest = (archive_dir / info.filename).resolve()
                if not str(dest).startswith(str(archive_dir.resolve())) or info.is_dir():
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(info))
                if dest.suffix.lower() not in SUPPORTED - {".zip"}:
                    errors.append(f"{rel(path)}::{info.filename}:unsupported:{dest.suffix.lower()}")
                    continue
                rr, ee, xx, seq = dispatch(dest, key, "supplement", f"{rel(path)}::{info.filename}", dpi, seq, tmp)
                rows.extend(rr); expected.update(ee); errors.extend(xx)
    except Exception as exc:
        errors.append(f"{rel(path)}:zip:{type(exc).__name__}:{clean(exc, 180)}")
    return rows, expected, errors, seq


def contact_sheets(rows: list[dict], key: str) -> list[str]:
    visual = [r for r in rows if r["vision_required"] == "Y" and r["image_path"]]
    if not visual:
        return []
    out_dir = OUT / "contact_sheets"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    tile_w, tile_h, cols, per_sheet = 720, 540, 2, 8
    for batch_i in range(0, len(visual), per_sheet):
        batch = visual[batch_i:batch_i + per_sheet]
        sheet = Image.new("RGB", (tile_w * cols, tile_h * ((len(batch) + cols - 1) // cols)), "#e8ebee")
        draw = ImageDraw.Draw(sheet)
        for i, row in enumerate(batch):
            tile = Image.new("RGB", (tile_w, tile_h), "white")
            im = Image.open(ROOT / row["image_path"]).convert("RGB")
            im.thumbnail((tile_w - 24, tile_h - 105))
            tile.paste(im, ((tile_w - im.width) // 2, 78))
            td = ImageDraw.Draw(tile)
            td.text((10, 8), row["object_id"], fill="black")
            td.text((10, 30), f"{row['source_scope']} | {row['object_label']} | {row['page_or_sheet']}", fill="#374151")
            td.text((10, 51), clean(row["caption"], 100), fill="#374151")
            sheet.paste(tile, ((i % cols) * tile_w, (i // cols) * tile_h))
        page = batch_i // per_sheet + 1
        target = out_dir / f"{safe(key)}__sheet_{page:03d}.jpg"
        sheet.save(target, quality=91, optimize=True)
        paths.append(rel(target))
    return paths


def write_tsv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows and not fields:
        path.write_text("", encoding="utf-8")
        return
    fields = fields or list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n")
        w.writeheader(); w.writerows(rows)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dpi", type=int, default=190)
    parser.add_argument("--study", action="append", help="restrict to one or more study keys")
    args = parser.parse_args()

    master = list(csv.DictReader(MASTER.open(encoding="utf-8-sig"), delimiter="\t"))
    active_keys = {r["key"] for r in master}
    if args.study:
        wanted = set(args.study)
        master = [r for r in master if r["key"] in wanted]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "objects").mkdir(exist_ok=True)
    (OUT / "vision_annotations").mkdir(exist_ok=True)

    all_rows, coverage = [], []
    for study_i, rec in enumerate(master, 1):
        key = rec["key"]
        study_dir = OUT / "objects" / key
        if study_dir.exists():
            shutil.rmtree(study_dir)
        study_dir.mkdir(parents=True)
        rows, expected, errors, seq = [], set(), [], 0
        main_pdf = ROOT / "references" / "pdf" / f"{key}.pdf"
        if main_pdf.exists():
            rr, ee, xx, seq = process_pdf(main_pdf, key, "main", rel(main_pdf), args.dpi, seq)
            rows.extend(rr); expected.update(ee); errors.extend(xx)
            main_status = "full_report_processed"
        else:
            main_status = "abstract_only_no_pdf"
        supp_dir = ROOT / "references" / "supplements" / key
        supp_files = []
        if supp_dir.exists():
            supp_files = [p for p in sorted(supp_dir.iterdir()) if p.is_file() and p.name not in IGNORE_SUPP]
        with tempfile.TemporaryDirectory(prefix=f"visual_{safe(key)}_") as td:
            tmp = Path(td)
            for path in supp_files:
                rr, ee, xx, seq = process_supplement(path, key, args.dpi, seq, tmp)
                rows.extend(rr); expected.update(ee); errors.extend(xx)
        extracted = {f"{r['source_path']}|{r['object_label']}" for r in rows
                     if not r["object_label"].startswith(("figure:UNLABELLED", "table:UNLABELLED"))}
        unmatched = sorted(expected - extracted)
        sheets = contact_sheets(rows, key)
        all_rows.extend(rows)
        pending = sum(r["chatgpt_vision_status"] in {"pending", "source_render_required"} for r in rows)
        coverage.append({
            "study_key": key, "title": rec.get("title", ""), "main_report_status": main_status,
            "supplement_files_processed": len(supp_files), "objects_total": len(rows),
            "main_figures": sum(r["source_scope"] == "main" and r["object_type"] == "figure" for r in rows),
            "main_tables": sum(r["source_scope"] == "main" and r["object_type"] == "table" for r in rows),
            "supplement_figures": sum(r["source_scope"] == "supplement" and r["object_type"] == "figure" for r in rows),
            "supplement_tables": sum(r["source_scope"] == "supplement" and r["object_type"] == "table" for r in rows),
            "vision_required": sum(r["vision_required"] == "Y" for r in rows),
            "chatgpt_vision_pending": pending,
            "expected_caption_labels": len(expected), "unmatched_caption_labels": len(unmatched),
            "unmatched_labels": ";".join(unmatched), "processing_errors": len(errors),
            "error_details": " | ".join(errors), "contact_sheets": ";".join(sheets),
            "zero_object_verification": (
                "not_assessable_abstract_only" if not rows and main_status == "abstract_only_no_pdf"
                else "native_text_has_no_figure_or_table_labels; page-image_review_required"
                if not rows else ""
            ),
            "audit_status": "needs_follow_up" if errors or unmatched or pending else "complete",
        })
        if study_i % 10 == 0 or study_i == len(master):
            print(f"processed {study_i}/{len(master)} studies; objects={len(all_rows)}; vision pending={sum(c['chatgpt_vision_pending'] for c in coverage)}", flush=True)

    # A restricted run refreshes only the requested studies while preserving the
    # previously audited ledger for every other study. This is the ingestion path
    # for newly obtained reports and prevents --study from truncating the corpus.
    if args.study and OBJECT_TSV.exists() and COVERAGE_TSV.exists():
        wanted = set(args.study)
        old_rows = [r for r in read_tsv(OBJECT_TSV) if r["study_key"] in active_keys and r["study_key"] not in wanted]
        old_coverage = [r for r in read_tsv(COVERAGE_TSV) if r["study_key"] in active_keys and r["study_key"] not in wanted]
        all_rows = old_rows + all_rows
        coverage = old_coverage + coverage
        all_rows.sort(key=lambda r: (r["study_key"], r["source_scope"], r["source_path"], r["object_id"]))
        coverage.sort(key=lambda r: r["study_key"])

    object_fields = list(base_row("", "", "", "", "").keys())
    write_tsv(OBJECT_TSV, all_rows, object_fields)
    write_tsv(COVERAGE_TSV, coverage)
    queue = [{
        "study_key": r["study_key"], "object_id": r["object_id"], "object_type": r["object_type"],
        "object_label": r["object_label"], "source_scope": r["source_scope"], "source_path": r["source_path"],
        "page_or_sheet": r["page_or_sheet"], "caption": r["caption"], "image_path": r["image_path"],
        "chatgpt_vision_status": r["chatgpt_vision_status"],
        "annotation_path": rel(OUT / "vision_annotations" / f"{r['object_id']}.json"),
    } for r in all_rows if r["vision_required"] == "Y"]
    write_tsv(QUEUE_TSV, queue)

    types = Counter((r["source_scope"], r["object_type"]) for r in all_rows)
    status = Counter(c["audit_status"] for c in coverage)
    lines = [
        "# Complete figure/table audit of included reports", "",
        "This is the exhaustive object-level inventory for the 222 included full-report studies. Mechanical extraction preserves native PDF/OOXML/spreadsheet text and exact table cells. Image-specific transcription and interpretation are performed only with ChatGPT vision; no OCR engine output is used.", "",
        f"- Included studies: {len(coverage)}",
        f"- Main reports processed: {sum(c['main_report_status'] == 'full_report_processed' for c in coverage)}; abstract-only/no local PDF: {sum(c['main_report_status'] != 'full_report_processed' for c in coverage)}",
        f"- Objects: {len(all_rows)}",
        f"- Main figures/tables: {types[('main','figure')]}/{types[('main','table')]}",
        f"- Supplement figures/tables: {types[('supplement','figure')]}/{types[('supplement','table')]}",
        f"- Objects requiring ChatGPT vision: {len(queue)}",
        f"- ChatGPT vision pending: {sum(int(c['chatgpt_vision_pending']) for c in coverage)}", "",
        "## Coverage status", "",
    ]
    lines += [f"- {k}: {v}" for k, v in sorted(status.items())]
    lines += ["", "## Study-level follow-up", "", "|Study|Objects|Vision pending|Unmatched caption labels|Errors|Status|", "|---|---:|---:|---:|---:|---|"]
    for c in coverage:
        lines.append(f"|{c['study_key']}|{c['objects_total']}|{c['chatgpt_vision_pending']}|{c['unmatched_caption_labels']}|{c['processing_errors']}|{c['audit_status']}|")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote objects={len(all_rows)} queue={len(queue)} coverage={len(coverage)}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Create high-resolution table-only images for six source-mapping repairs."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "data/tmp_table_mapping_audit"
OUT = ROOT / "data/visual_manual_review/latest_after_recrop/decoded_recovered/table"
OUT.mkdir(parents=True, exist_ok=True)


def crop(src, box, name):
    with Image.open(TMP / src) as im:
        im.crop(box).save(OUT / name)


def main():
    crop("choi_p13.png", (150, 400, 1815, 1050),
         "choi2026development__0001__table_1__table_only.png")

    with Image.open(TMP / "kang_p7.png") as im:
        page = im.rotate(-90, expand=True)
        # The PDF has an incorrect page-rotation flag. Table 2 is in the
        # upper-left quadrant after normalizing that page coordinate system.
        table = page.crop((120, 140, 1410, 1080)).rotate(90, expand=True)
        table.save(OUT / "kang2019sarcopenia__0007__table_2_recovered__table_only.png")

    with Image.open(TMP / "oh-04.png") as a, Image.open(TMP / "oh-05.png") as b:
        first = a.crop((115, 190, 1990, 2485))
        second = b.crop((125, 170, 2070, 1030)).resize((1875, 829), Image.Resampling.LANCZOS)
        joined = Image.new("RGB", (1875, first.height + second.height + 24), "white")
        joined.paste(first, (0, 0)); joined.paste(second, (0, first.height + 24))
        joined.save(OUT / "oh2015artificial__0006__table_1_recovered__complete_table.png")

    crop("tran-04.png", (75, 1110, 1010, 2185),
         "tran2024explainable__0016__table_2_recovered__table_only.png")
    crop("ullah-08.png", (100, 150, 1885, 690),
         "ullah2023machine__0004__table_2_recovered__table_only.png")
    crop("ullah-08.png", (100, 745, 1885, 1370),
         "ullah2023machine__0005__table_3_recovered__table_only.png")
    crop("kim_s1/page-1.png", (145, 245, 1935, 1435),
         "kim2024gender__0002__table_S1__table_only.png")

    for p in sorted(OUT.glob("*__table_only.png")):
        if any(x in p.name for x in ("choi2026", "kang2019", "tran2024", "ullah2023", "kim2024")):
            with Image.open(p) as im: print(p.name, im.size)
    p = OUT / "oh2015artificial__0006__table_1_recovered__complete_table.png"
    with Image.open(p) as im: print(p.name, im.size)


if __name__ == "__main__":
    main()

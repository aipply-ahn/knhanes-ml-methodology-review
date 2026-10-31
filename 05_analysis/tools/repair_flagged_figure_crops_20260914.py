#!/usr/bin/env python3
"""Create figure-only, high-resolution crops for five visually flagged objects."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TMP = Path('/tmp/visual_repair_20260914')
OUT = ROOT / 'data/visual_manual_review/latest_after_recrop/decoded_recovered/figure'

def crop(src, box, dst, rotate=0):
    with Image.open(src) as im:
        x = im.crop(box)
        if rotate:
            x = x.rotate(rotate, expand=True)
        x.save(OUT / dst, dpi=(240, 240), optimize=True)
        print(dst, x.size)

crop(TMP/'jo_p7.png', (140, 350, 1845, 2410),
     'jo2023development__0005__figure_2__figure_only_upright.png', rotate=-90)
crop(TMP/'kim_p6.png', (535, 1010, 1515, 2185),
     'kim2024machinea__0001__figure_1__figure_only.png')
crop(TMP/'ko-09.png', (300, 155, 1190, 1090),
     'ko2025weight__0005__figure_2__figure_only.png')
crop(TMP/'suhfig-11.png', (145, 505, 1845, 1785),
     'suh2023interpretable__0007__figure_5__figure_only.png')
crop(TMP/'suhfig-12.png', (145, 565, 1845, 2010),
     'suh2023interpretable__0008__figure_6__figure_only.png')

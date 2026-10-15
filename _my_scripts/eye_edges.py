"""Measure the eye white + iris region per column and compare it with the rig's eye opening.

Classifies pixels inside each eye roi as white, iris or other, keeps the largest connected
white+iris region and prints its top and bottom edge per column next to the polygon's.

usage: uv run --with numpy --with pillow --with opencv-python-headless my-scripts/eye_edges.py <project> <rig.json>
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

project, rig_name = Path(sys.argv[1]), sys.argv[2]
rig = json.loads((project / rig_name).read_text(encoding="utf-8"))
img = np.asarray(Image.open(project / "source.png").convert("RGB")).astype(int)
r, g, b = img[..., 0], img[..., 1], img[..., 2]
white = (r > 215) & (g > 215) & (b > 215) & (np.ptp(img, axis=2) < 30)
iris = (r > 90) & (r - g > 70) & (r - b > 60) & (g < 150)
pale_white = (b > 200) & (g > 200) & (np.ptp(img, axis=2) < 40)  # bluish-grey shaded white
eye_px = white | iris | pale_white

for index, eye in enumerate(rig["eyes"]):
    roi = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(roi, [np.array(eye["roi"], np.int32)], 1)
    region = (eye_px & roi.astype(bool)).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(region, 4)
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    region = labels == largest
    opening = np.zeros(img.shape[:2], np.uint8)
    cv2.fillPoly(opening, [np.array(eye["opening"], np.int32)], 1)
    opening = opening.astype(bool)

    xs = np.where(region.any(axis=0))[0]
    print(f"eye {index}: measured x {xs.min()}..{xs.max()}, opening x "
          f"{min(p[0] for p in eye['opening'])}..{max(p[0] for p in eye['opening'])}")
    print("   x | measured top..bot | polygon top..bot")
    for x in range(xs.min(), xs.max() + 1, 2):
        ys = np.where(region[:, x])[0]
        ps = np.where(opening[:, x])[0]
        m = f"{ys.min():3d}..{ys.max():3d}" if len(ys) else "   -    "
        p = f"{ps.min():3d}..{ps.max():3d}" if len(ps) else "   -    "
        print(f" {x:3d} | {m}          | {p}")
    inside = region & opening
    print(f"   measured eye pixels covered by opening: {inside.sum() / region.sum():.1%}; "
          f"opening pixels that are not eye: {(opening & ~region).sum() / opening.sum():.1%}\n")

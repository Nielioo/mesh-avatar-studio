"""Print a character map of a source region to check outlines pixel by pixel.

W eye white (incl. shaded), I iris (red), L dark line/lash, S skin, H hair, . other.
Rows and columns are labelled in source pixels. Optional polygon from the rig marks its
vertices with '#'.

usage: uv run --with numpy --with pillow my-scripts/pixel_map.py <project> x0,y0,x1,y1 [rig.json eye-index part]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

project = Path(sys.argv[1])
x0, y0, x1, y1 = map(int, sys.argv[2].split(","))
marks = set()
if len(sys.argv) > 5:
    rig = json.loads((project / sys.argv[3]).read_text(encoding="utf-8"))
    marks = {(round(x), round(y)) for x, y in rig["eyes"][int(sys.argv[4])][sys.argv[5]]}

a = np.asarray(Image.open(project / "source.png").convert("RGB")).astype(int)


def classify(r, g, b):
    if r > 150 and g > 140 and b > 140 and max(r, g, b) - min(r, g, b) < 35:
        return "W"
    if r - g > 30 and g < 130:
        return "I"
    if r + g + b < 260:
        return "L"
    if r > 200 and g > 150 and b < 130:
        return "H"
    if r > 200 and r - b > 25:
        return "S"
    return "."


print("     " + "".join(str(x // 10 % 10) if x % 10 == 0 else " " for x in range(x0, x1)))
print("     " + "".join(str(x % 10) for x in range(x0, x1)))
for y in range(y0, y1):
    row = "".join("#" if (x, y) in marks else classify(*a[y, x]) for x in range(x0, x1))
    print(f"{y:4d} {row}")

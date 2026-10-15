"""Draw one eye's opening and roi polygons over a 10x crop of source.png for close review.

usage: uv run --with pillow my-scripts/eye_zoom.py <project> <rig.json> <eye index> <out.png>
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

SCALE = 10
project, rig_name, index, out = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), sys.argv[4]
rig = json.loads((project / rig_name).read_text(encoding="utf-8"))
eye = rig["eyes"][index]
points = eye["opening"] + eye["roi"]
x0 = int(min(p[0] for p in points)) - 6
y0 = int(min(p[1] for p in points)) - 6
x1 = int(max(p[0] for p in points)) + 6
y1 = int(max(p[1] for p in points)) + 6

src = Image.open(project / "source.png").convert("RGBA")
bg = Image.new("RGBA", src.size, (128, 128, 128, 255))
bg.alpha_composite(src)
crop = bg.crop((x0, y0, x1, y1)).resize(((x1 - x0) * SCALE, (y1 - y0) * SCALE), Image.NEAREST)
draw = ImageDraw.Draw(crop)


def to_view(p):
    # Pixel centres: source coordinate x maps to the middle of its enlarged pixel.
    return ((p[0] - x0 + 0.5) * SCALE, (p[1] - y0 + 0.5) * SCALE)


for gx in range(x0 - x0 % 5 + 5, x1, 5):
    draw.line([to_view((gx - 0.5, y0))[0], 0, to_view((gx - 0.5, y0))[0], crop.height], fill=(90, 90, 255, 255), width=1)
    draw.text((to_view((gx - 0.5, y0))[0] + 2, 2), str(gx), fill=(0, 0, 160, 255))
for gy in range(y0 - y0 % 5 + 5, y1, 5):
    draw.line([0, to_view((x0, gy - 0.5))[1], crop.width, to_view((x0, gy - 0.5))[1]], fill=(90, 90, 255, 255), width=1)
    draw.text((2, to_view((x0, gy - 0.5))[1] + 2), str(gy), fill=(0, 0, 160, 255))

for name, colour in (("roi", (255, 160, 0, 255)), ("opening", (0, 255, 120, 255))):
    poly = [to_view(p) for p in eye[name]]
    draw.line(poly + [poly[0]], fill=colour, width=2)
    for i, p in enumerate(poly):
        draw.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], outline=colour, width=2)
        draw.text((p[0] + 5, p[1] - 12), str(i), fill=colour)

crop.convert("RGB").save(out)
print(f"{out}: eye {index}, source box {x0},{y0}-{x1},{y1}, scale {SCALE}")

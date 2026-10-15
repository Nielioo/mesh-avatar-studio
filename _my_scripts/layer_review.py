"""Make review images for Check 4: the hair mask tinted over the source, and every eye layer
placed at its offset (from built/layers.json) on magenta, enlarged.

usage: uv run --with numpy --with pillow my-scripts/layer_review.py <project>
writes <project>/work/check-hairmask.png and <project>/work/check-eyelayers.png
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

project = Path(sys.argv[1])
built = project / "built"
layers = json.loads((built / "layers.json").read_text(encoding="utf-8"))
src = Image.open(project / "source.png").convert("RGBA")
w, h = src.size

grey = Image.new("RGBA", src.size, (128, 128, 128, 255))
grey.alpha_composite(src)
base = np.asarray(grey.convert("RGB")).astype(float)
mask = np.asarray(Image.open(built / "hairmask.png").convert("L")).astype(float)[..., None] / 255
tint = base * (1 - 0.55 * mask) + np.array([0, 255, 90]) * 0.55 * mask
ys, xs = np.where(mask[..., 0] > 0.05)
pad = 30
box = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(w, xs.max() + pad), min(h, ys.max() + pad))
Image.fromarray(tint.astype(np.uint8)).crop(box).save(project / "work" / "check-hairmask.png")

eyes = sorted({name.split("_")[0] for name in layers["layers"] if name.startswith("eye")})
kinds = ["ball", "lash", "low", "crease"]
scale, tiles = 5, []
for eye in eyes:
    rects = [layers["layers"][f"{eye}_{k}"] for k in kinds if f"{eye}_{k}" in layers["layers"]]
    x0 = min(r[0] for r in rects) - 4
    y0 = min(r[1] for r in rects) - 4
    x1 = max(r[0] + r[2] for r in rects) + 4
    y1 = max(r[1] + r[3] for r in rects) + 4
    for kind in kinds + ["all"]:
        canvas = Image.new("RGBA", (w, h), (255, 0, 255, 255))
        for k in (kinds if kind == "all" else [kind]):
            name = f"{eye}_{k}"
            if name in layers["layers"]:
                x, y, _, _ = layers["layers"][name]
                canvas.alpha_composite(Image.open(built / f"{name}.png").convert("RGBA"), (x, y))
        tile = canvas.crop((x0, y0, x1, y1)).resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
        ImageDraw.Draw(tile).text((4, 2), f"{eye} {kind}", fill=(255, 255, 255, 255))
        tiles.append(tile.convert("RGB"))

cols = len(kinds) + 1
tw = max(t.width for t in tiles)
th = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * (tw + 4), (len(tiles) // cols) * (th + 4)), (40, 40, 40))
for i, tile in enumerate(tiles):
    sheet.paste(tile, ((i % cols) * (tw + 4), (i // cols) * (th + 4)))
sheet.save(project / "work" / "check-eyelayers.png")
print("wrote work/check-hairmask.png and work/check-eyelayers.png")

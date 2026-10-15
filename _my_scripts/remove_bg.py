"""Remove a flat gray background from a sticker-style illustration (local, no network).

usage: remove_bg.py <in.jpg> <out.png> [x0 y0 x1 y1] [--keep-left-of X]
"""
import sys

import cv2
import numpy as np
from PIL import Image

args = [a for a in sys.argv[1:]]
keep_left = None
if "--keep-left-of" in args:
    i = args.index("--keep-left-of")
    keep_left = int(args[i + 1])
    del args[i:i + 2]
src, dst = args[0], args[1]
img = np.asarray(Image.open(src).convert("RGB")).astype(np.float32)
if len(args) == 6:
    x0, y0, x1, y1 = map(int, args[2:6])
    img = img[y0:y1, x0:x1]
    if keep_left is not None:
        keep_left -= x0

h, w, _ = img.shape
# Background colour: median of the image border.
border = np.concatenate([img[:8].reshape(-1, 3), img[-8:].reshape(-1, 3),
                         img[:, :8].reshape(-1, 3), img[:, -8:].reshape(-1, 3)])
bg = np.median(border, axis=0)

diff = np.abs(img - bg)
dist = diff.max(axis=2)
chroma = img.max(axis=2) - img.min(axis=2)
# Pure background: close to bg colour and nearly achromatic.
is_bg = (dist < 14) & (chroma < 12)
is_bg = cv2.morphologyEx(is_bg.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)).astype(bool)

alpha = np.where(is_bg, 0.0, 1.0)
# Soft edge band next to the background: the sticker outline is white, so estimate
# coverage from how far each pixel moved from bg towards white.
band = cv2.dilate(is_bg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~is_bg
lum = img.mean(axis=2)
white = 250.0
cover = np.clip((lum - bg.mean()) / (white - bg.mean()), 0, 1)
dark_cover = np.clip((bg.mean() - lum) / 60.0, 0, 1)  # edges touching dark lines directly
alpha[band] = np.maximum(cover, dark_cover)[band]

# Keep only the figure: drop small specks and anything right of keep_left (e.g. back view).
solid = (alpha > 0.5).astype(np.uint8)
n, labels, stats, _ = cv2.connectedComponentsWithStats(solid, 8)
keep = np.zeros(n, bool)
for i in range(1, n):
    x, y, bw, bh, area = stats[i]
    if area < 200:
        continue
    if keep_left is not None and x >= keep_left:
        continue
    keep[i] = True
mask = keep[labels]
mask = cv2.dilate(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
alpha[~mask] = 0

# Unmix the background colour from partially transparent pixels.
a3 = alpha[..., None]
fg = np.where(a3 > 0.02, (img - (1 - a3) * bg) / np.maximum(a3, 0.02), img)
fg = np.clip(fg, 0, 255)
out = np.dstack([fg, alpha * 255]).round().astype(np.uint8)
Image.fromarray(out, "RGBA").save(dst)
print(f"{dst}: {w}x{h}, bg={bg.round(1)}, opaque={np.mean(alpha > 0.5):.1%}")

"""Put the same crop of several review frames side by side, enlarged, for close comparison.

usage: uv run --with pillow my-scripts/compare_frames.py <review dir> x0,y0,x1,y1 <scale> <out.png> frame [frame ...]
Coordinates are in review-frame pixels; frames are names without .png (e.g. rest turn-left).
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

review, box, scale, out = Path(sys.argv[1]), tuple(map(int, sys.argv[2].split(","))), int(sys.argv[3]), sys.argv[4]
names = sys.argv[5:]
tiles = []
for name in names:
    frame = Image.open(review / f"{name}.png").convert("RGBA")
    bg = Image.new("RGBA", frame.size, (128, 128, 128, 255))
    bg.alpha_composite(frame)
    tile = bg.crop(box).resize(((box[2] - box[0]) * scale, (box[3] - box[1]) * scale), Image.LANCZOS)
    ImageDraw.Draw(tile).text((6, 4), name, fill=(255, 255, 0, 255))
    tiles.append(tile.convert("RGB"))
sheet = Image.new("RGB", (sum(t.width + 4 for t in tiles), tiles[0].height), (30, 30, 30))
x = 0
for tile in tiles:
    sheet.paste(tile, (x, 0))
    x += tile.width + 4
sheet.save(out)
print(out)

"""Turns frames from render_loops.mjs into looping transparent GIFs.

uv run --with pillow _my_scripts/make_gif.py projects/<name> [height | WxH] [clip ...]

Crops every clip to the same box (the union of all frames, so the avatar does not jump when
an overlay swaps the idle GIF for the talking one), scales to `height` px, or fits
it into a WxH canvas (default 512x512, centred, standing on the bottom edge), and writes
projects/<name>/gif/<clip>_<size>.gif (not git-ignored) with ffmpeg's palette generation.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

project = Path(sys.argv[1])
size_arg = sys.argv[2] if len(sys.argv) > 2 else "512x512"
canvas = tuple(int(v) for v in size_arg.split("x")) if "x" in size_arg else None
gif_dir = project / "work" / "gif"
clips = sys.argv[3:] or ["idle", "talk"]

frames = {c: sorted((gif_dir / c).glob("frame_*.png")) for c in clips}
box = None
for files in frames.values():
    for f in files:
        b = Image.open(f).getbbox()
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
size = Image.open(frames[clips[0]][0]).size
pad = 6
box = (max(0, box[0] - pad), max(0, box[1] - pad), min(size[0], box[2] + pad), min(size[1], box[3]))
bw, bh = box[2] - box[0], box[3] - box[1]
if canvas:
    k = min(canvas[0] / bw, canvas[1] / bh)
    width, height = round(bw * k), round(bh * k)
else:
    height = int(size_arg)
    width = round(bw * height / bh)
out_size = canvas or (width, height)

for clip, files in frames.items():
    scaled = gif_dir / f"{clip}_{size_arg}"
    shutil.rmtree(scaled, ignore_errors=True)
    scaled.mkdir()
    for i, f in enumerate(files):
        # Pillow resizes RGBA with premultiplied alpha: no dark fringe from transparent pixels
        frame = Image.open(f).crop(box).resize((width, height), Image.LANCZOS)
        if canvas:
            square = Image.new("RGBA", canvas, (0, 0, 0, 0))
            square.paste(frame, ((canvas[0] - width) // 2, canvas[1] - height))
            frame = square
        frame.save(scaled / f"{i:04d}.png")
    fps = json.loads((gif_dir / clip / "clip.json").read_text())["fps"]
    out = project / "gif" / f"{clip}_{size_arg}.gif"
    out.parent.mkdir(exist_ok=True)
    subprocess.run([
        "ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", str(scaled / "%04d.png"),
        "-filter_complex",
        "[0:v]split[a][b];[a]palettegen=reserve_transparent=1:stats_mode=full:max_colors=256[p];"
        "[b][p]paletteuse=dither=none:alpha_threshold=128:diff_mode=rectangle",
        "-loop", "0", str(out),
    ], check=True)
    print(json.dumps({"gif": str(out), "frames": len(files), "size": list(out_size), "kB": out.stat().st_size // 1024}))

# _my_scripts

Helper scripts used while preparing an avatar from my own illustration. They read from a
project in `projects/` and write review images to its `work/` folder; nothing is uploaded.
Run them from the repository root with uv.

| Script | What it does |
|---|---|
| `remove_bg.py` | Removes a flat background colour from a sticker-style illustration and optionally crops it. `uv run --with numpy --with pillow --with opencv-python-headless _my_scripts/remove_bg.py in.jpg out.png [x0 y0 x1 y1] [--keep-left-of X]` |
| `eye_zoom.py` | Draws one eye's `opening` and `roi` polygons over a 10x crop of `source.png`. `uv run --with pillow _my_scripts/eye_zoom.py projects/<name> rig.draft.json <eye> <out.png>` |
| `pixel_map.py` | Prints a character map of a region (W white, I iris/red, L dark line, S skin, H hair) to place eye outlines pixel by pixel. `uv run --with numpy --with pillow _my_scripts/pixel_map.py projects/<name> x0,y0,x1,y1 [rig.draft.json <eye> opening]` |
| `eye_edges.py` | Measures the eye white and iris per column and compares them with the rig's eye opening. |
| `layer_review.py` | Check 4 images: hair mask tinted over the source, and every eye layer at its offset. `uv run --with numpy --with pillow _my_scripts/layer_review.py projects/<name>` |
| `compare_frames.py` | Puts the same crop of several `review/` frames side by side. `uv run --with pillow _my_scripts/compare_frames.py projects/<name>/review x0,y0,x1,y1 <scale> <out.png> rest turn-left ...` |

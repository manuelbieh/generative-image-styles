#!/usr/bin/env python3
"""Render <set-dir>/dist/og.jpg (1200x630 social preview) from the dist thumbnails.

Builds a tilted mosaic of style thumbnails with a title overlay as HTML,
screenshots it with headless Chrome, then converts it to JPEG.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
COLUMNS, ROWS = 11, 7

set_dir = Path(__file__).parent / (sys.argv[1] if len(sys.argv) > 1 else "set-2")
dist = set_dir / "dist"
thumbs = sorted((p for p in (dist / "thumbs").glob("*.webp") if "ghibli" not in p.stem),
                key=lambda p: int(p.stem.split("-")[0]))
count = len(thumbs)
needed = COLUMNS * ROWS
step = count / needed
picks = [thumbs[int(i * step)] for i in range(needed)]
tiles = "\n".join(f'<img src="{p.as_uri()}">' for p in picks)

html = f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  * {{ box-sizing: border-box; margin: 0; }}
  html, body {{ width: 1200px; height: 630px; overflow: hidden; background: #111013; }}
  .mosaic {{ position: absolute; left: 50%; top: 50%; display: grid; gap: 10px;
    grid-template-columns: repeat({COLUMNS}, 150px);
    transform: translate(-42%, -50%) rotate(-9deg); }}
  .mosaic img {{ width: 150px; height: 150px; object-fit: cover; border-radius: 10px; display: block; }}
  .scrim {{ position: absolute; inset: 0;
    background: linear-gradient(90deg, rgb(17 16 19 / .96) 0%, rgb(17 16 19 / .9) 38%, rgb(17 16 19 / .35) 62%, rgb(17 16 19 / 0) 80%); }}
  .text {{ position: absolute; left: 72px; top: 50%; transform: translateY(-50%); width: 560px; color: #f4f2ee; }}
  .eyebrow {{ font: 600 20px/1 "Inter Display", Inter, sans-serif; letter-spacing: .16em; text-transform: uppercase; color: #e0b040; margin-bottom: 22px; }}
  h1 {{ font: 800 84px/0.95 "Inter Display", Inter, sans-serif; letter-spacing: -.035em; }}
  h1 em {{ font: italic 500 92px/0.95 "Cormorant Garamond", serif; letter-spacing: -.01em; color: #e0b040; }}
  p {{ text-wrap: balance; margin-top: 26px; font: 400 25px/1.4 Inter, sans-serif; color: #b9b6b0; }}
</style></head><body>
<div class="mosaic">{tiles}</div>
<div class="scrim"></div>
<div class="text">
  <div class="eyebrow">Art Style References</div>
  <h1>One character.<br><em>So many styles.</em></h1>
  <p>From oil paintings and comics to pixel art and claymation. A filterable gallery of style references.</p>
</div>
</body></html>"""

with tempfile.TemporaryDirectory() as tmp:
    page = Path(tmp) / "og.html"
    png = Path(tmp) / "og.png"
    page.write_text(html)
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                    "--force-device-scale-factor=1", "--window-size=1200,630", "--virtual-time-budget=5000",
                    f"--screenshot={png}", page.as_uri()], check=True, capture_output=True)
    subprocess.run(["magick", str(png), "-quality", "88", "-strip", str(dist / "og.jpg")], check=True)
print(f"wrote {dist / 'og.jpg'}")

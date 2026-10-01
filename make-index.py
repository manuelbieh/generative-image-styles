#!/usr/bin/env python3
"""Build <set-dir>/index.html from <set-dir>/styles.tsv.

styles.tsv columns: file-stem, title, prompt description, comma-separated tags.
Filtering, pagination and lazy loading happen client-side.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

PAGE_SIZE = 200
TAG_LABELS = {
    "art": "Fine Art",
    "illustration": "Illustration",
    "comics": "Comics",
    "tv": "TV",
    "film": "Film",
    "anime": "Anime",
    "games": "Games",
    "3d": "3D",
    "photo": "Photo",
    "print": "Print & Design",
    "craft": "Craft",
    "folk": "Folk",
    "toys": "Toys",
    "experimental": "Experimental",
    "decades": "Decades",
}

args = [a for a in sys.argv[1:] if not a.startswith("--")]
dist = "--dist" in sys.argv
set_dir = Path(__file__).parent / (args[0] if args else "set-2")
out_dir = set_dir / "dist" if dist else set_dir
reference_file = "reference.jpg" if dist else "reference.png"
prompts_file = set_dir / "prompts.json"
prompts = json.loads(prompts_file.read_text()) if prompts_file.exists() else {}
# Original generation prompts stay in prompts.json. The site shows the reusable
# style prompt, which does not describe the gallery character and must work both with an
# attached reference image and with a scene described in text.
style_prompts_file = set_dir / "style-prompts.json"
style_prompts = json.loads(style_prompts_file.read_text()) if style_prompts_file.exists() else {}
shown_prompts = style_prompts or prompts
styles = []
for line in (set_dir / "styles.tsv").read_text().splitlines():
    if not line.strip():
        continue
    cols = line.split("\t")
    stem, title, desc = cols[0], cols[1], cols[2]
    tags = [t for t in (cols[3] if len(cols) > 3 else "").split(",") if t]
    if not (set_dir / "styles" / f"{stem}.png").exists():
        continue
    styles.append({
        "n": int(stem.split("-")[0]),
        "file": f"full/{stem}.jpg" if dist else f"styles/{stem}.png",
        "thumb": f"thumbs/{stem}.webp" if dist else f"styles/{stem}.png",
        "title": title,
        "desc": desc,
        "tags": tags,
        "stem": stem,
        "hasPrompt": stem in shown_prompts,
    })

unknown = {t for s in styles for t in s["tags"]} - TAG_LABELS.keys()
if unknown:
    sys.exit(f"unknown tags: {', '.join(sorted(unknown))}")

source_bound = [stem for stem, text in style_prompts.items() if re.search(r"\breference\b", text, re.I)]
if source_bound:
    sys.exit(f"style prompts must not assume a reference image: {', '.join(source_bound)}")

reference = ""
if (set_dir / "reference.png").exists():
    reference = f"""
<section class="reference">
  <a href="{reference_file}" target="_blank"><img src="{reference_file}" alt="Original photorealistic reference" width="320" height="320"></a>
  <div>
    <strong>Original reference</strong>
    <span>Photorealistic base image of the character: curly auburn hair, freckles, round tortoiseshell glasses, mustard-yellow knit sweater, coffee and a croissant in a cafe.</span>
  </div>
</section>"""

# Prompts are about 1 MB, so they live in a script that loads on first use instead of in the page.
# A script tag (unlike fetch) also works when index.html is opened straight from disk.
prompts_js = "window.stylePrompts = " + json.dumps({s["stem"]: shown_prompts[s["stem"]] for s in styles if s["hasPrompt"]}, ensure_ascii=False) + ";\n"
prompts_src = f"prompts.js?v={hashlib.sha1(prompts_js.encode()).hexdigest()[:10]}"

data = json.dumps({"pageSize": PAGE_SIZE, "tagLabels": TAG_LABELS, "promptsSrc": prompts_src, "styles": styles}, ensure_ascii=False)
data = data.replace("</", "<\\/")

SITE_URL = "https://imagestyles.manuelbieh.online/"
og_title = f"Art Style References: one character, {len(styles)} styles"
og_desc = "The same character drawn in {n} art styles, from oil paintings and comics to pixel art and claymation. Filter by tag and use them as style references for image prompts.".format(n=len(styles))
social_meta = f"""<meta name="description" content="{og_desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{og_desc}">
<meta property="og:image" content="{SITE_URL}og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A mosaic of the same curly-haired character in dozens of art styles">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{og_desc}">
<meta name="twitter:image" content="{SITE_URL}og.jpg">
""" if dist else ""

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Art Style References</title>
{social_meta}<style>
  :root {{ --bg: #f4f2ee; --card: #fff; --text: #1d1d1f; --muted: #6b6b70; --line: #dcd8d0; --accent: #b8860b; --accent-text: #fff; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #141416; --card: #1f1f22; --text: #f2f2f2; --muted: #9a9aa0; --line: #34343a; --accent: #e0b040; --accent-text: #141416; }} }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 32px 16px; background: var(--bg); color: var(--text); font: 15px/1.45 system-ui, sans-serif; }}
  header, .reference, .controls, main, .pager {{ max-width: 1400px; margin-left: auto; margin-right: auto; }}
  header {{ margin-bottom: 24px; }}
  h1 {{ margin: 0 0 4px; font-size: 28px; }}
  header p {{ margin: 0; color: var(--muted); }}
  .reference {{ margin-bottom: 28px; display: flex; gap: 20px; align-items: flex-start; background: var(--card); border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgb(0 0 0 / .12); }}
  .reference a {{ flex: 0 0 min(320px, 40%); border-radius: 8px; overflow: hidden; }}
  .reference img {{ display: block; width: 100%; height: auto; }}
  .reference strong {{ display: block; font-size: 18px; margin-bottom: 6px; }}
  .reference span {{ color: var(--muted); }}
  .controls {{ position: sticky; top: 0; z-index: 10; background: var(--bg); padding: 12px 0; margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; flex: 1 1 600px; }}
  .chip {{ font: inherit; font-size: 14px; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--line); background: var(--card); color: var(--text); cursor: pointer; }}
  .chip:hover {{ border-color: var(--accent); }}
  .chip[aria-pressed="true"] {{ background: var(--accent); border-color: var(--accent); color: var(--accent-text); }}
  .chip .count {{ opacity: .65; margin-left: 4px; font-variant-numeric: tabular-nums; }}
  .chip[data-shared] {{ border-style: dashed; }}
  #share-note {{ flex-basis: 100%; margin: 0; }}
  input[type="search"] {{ font: inherit; padding: 7px 12px; border-radius: 8px; border: 1px solid var(--line); background: var(--card); color: var(--text); min-width: 220px; flex: 0 1 280px; }}
  .status {{ max-width: 1400px; margin: 0 auto 16px; color: var(--muted); font-size: 14px; }}
  main {{ display: grid; gap: 20px; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }}
  figure {{ position: relative; margin: 0; background: var(--card); border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgb(0 0 0 / .12); }}
  figure a {{ display: block; overflow: hidden; aspect-ratio: 1; background: var(--line); }}
  figure img {{ display: block; width: 100%; height: 100%; object-fit: cover; transition: transform .2s; }}
  figure a:hover img {{ transform: scale(1.03); }}
  .prompt-button {{ position: absolute; top: 10px; right: 10px; display: grid; place-items: center; width: 36px; height: 36px; padding: 0; border-radius: 999px; border: 1px solid rgb(255 255 255 / .28); background: rgb(20 20 22 / .55); color: #fff; cursor: pointer; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); transition: background-color .15s; }}
  .prompt-button:hover {{ background: rgb(20 20 22 / .8); }}
  .save-control {{ position: absolute; top: 10px; left: 10px; display: flex; }}
  .save-button, .save-more {{ display: grid; place-items: center; height: 36px; padding: 0; border: 1px solid rgb(255 255 255 / .28); background: rgb(20 20 22 / .55); color: #fff; cursor: pointer; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); }}
  .save-button {{ width: 36px; border-radius: 999px 0 0 999px; }}
  .save-more {{ width: 28px; border-radius: 0 999px 999px 0; border-left: none; }}
  .save-button:hover, .save-more:hover, .prompt-button:hover {{ background: rgb(20 20 22 / .8); }}
  .save-button[aria-pressed="true"] {{ background: var(--accent); border-color: var(--accent); color: var(--accent-text); }}
  .save-button[aria-pressed="true"] svg {{ fill: currentColor; }}
  .save-button[aria-pressed="true"] + .save-more {{ border-color: var(--accent); }}
  .save-more[data-collected="true"] {{ color: var(--accent); }}
  .prompt-button:focus-visible, .save-button:focus-visible, .save-more:focus-visible, .dialog-close:focus-visible, .copy-button:focus-visible, .text-button:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
  .prompt-button svg, .save-button svg, .save-more svg, .dialog-close svg, .copy-button svg {{ width: 18px; height: 18px; flex: none; }}
  .text-button, .small-button {{ font: inherit; border-radius: 8px; border: 1px solid var(--line); background: var(--card); color: var(--text); cursor: pointer; }}
  .text-button {{ font-size: 14px; padding: 7px 12px; }}
  .small-button {{ font-size: 13px; padding: 6px 10px; }}
  .text-button:hover, .small-button:hover {{ border-color: var(--accent); }}
  #collection-chips {{ flex-basis: 100%; }}
  #collection-chips:empty {{ display: none; }}
  .check-list, .manager-list {{ display: flex; flex-direction: column; gap: 8px; margin: 0; padding: 0; list-style: none; max-height: min(240px, 40dvh); overflow: auto; }}
  .check-list label {{ display: flex; align-items: center; gap: 10px; min-height: 32px; cursor: pointer; }}
  .collection-create, .manager-item {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }}
  .collection-create input, .manager-item input, .io textarea {{ font: inherit; border-radius: 8px; border: 1px solid var(--line); background: var(--bg); color: var(--text); }}
  .collection-create input, .manager-item input {{ padding: 7px 12px; min-width: 0; }}
  .collection-create input {{ flex: 1; }}
  .manager-item .name {{ font-weight: 600; }}
  .manager-item .meta, .dialog-note, .io-status {{ color: var(--muted); font-size: 13px; }}
  .manager-item input {{ flex: 1 1 140px; }}
  .danger {{ font: inherit; font-size: 13px; padding: 6px 10px; border-radius: 8px; border: 1px solid var(--line); background: none; color: var(--muted); cursor: pointer; }}
  .danger:hover {{ border-color: #a33; color: #a33; }}
  .io {{ display: flex; flex-direction: column; gap: 8px; }}
  .io h3 {{ margin: 8px 0 0; font-size: 15px; }}
  .io textarea {{ font-size: 13px; line-height: 1.45; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; width: 100%; min-height: 72px; resize: vertical; padding: 10px 12px; }}
  .dialog-note {{ margin: 0; }}
  figcaption {{ padding: 12px 14px 14px; }}
  figcaption strong {{ display: block; margin-bottom: 4px; }}
  figcaption .desc {{ color: var(--muted); font-size: 13px; }}
  .tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }}
  .tag {{ font: inherit; font-size: 12px; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); background: none; color: var(--muted); cursor: pointer; }}
  .tag:hover {{ color: var(--text); border-color: var(--accent); }}
  .empty {{ grid-column: 1 / -1; text-align: center; color: var(--muted); padding: 48px 0; }}
  .pager {{ display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-top: 24px; margin-bottom: 24px; }}
  .pager:empty {{ display: none; }}
  .pager button {{ font: inherit; min-width: 40px; padding: 6px 12px; border-radius: 8px; border: 1px solid var(--line); background: var(--card); color: var(--text); cursor: pointer; }}
  .pager button[aria-current="page"] {{ background: var(--accent); border-color: var(--accent); color: var(--accent-text); }}
  .pager button:disabled {{ opacity: .4; cursor: default; }}
  body:has(dialog[open]) {{ overflow: hidden; }}
  dialog {{ width: min(680px, calc(100vw - 32px)); max-height: calc(100dvh - 32px); padding: 0; border: none; border-radius: 12px; background: var(--card); color: var(--text); box-shadow: 0 12px 40px rgb(0 0 0 / .35); }}
  dialog::backdrop {{ background: rgb(0 0 0 / .55); }}
  .dialog-inner {{ display: flex; flex-direction: column; gap: 14px; max-height: calc(100dvh - 32px); padding: 18px 20px 20px; }}
  .dialog-head {{ display: flex; align-items: flex-start; gap: 12px; }}
  .dialog-head > div {{ flex: 1; }}
  .dialog-head h2 {{ margin: 0; font-size: 18px; line-height: 1.35; text-wrap: balance; }}
  .dialog-head p {{ margin: 2px 0 0; color: var(--muted); font-size: 13px; }}
  .dialog-close {{ display: grid; place-items: center; width: 36px; height: 36px; margin: -6px -8px 0 0; padding: 0; border: none; border-radius: 8px; background: none; color: var(--muted); cursor: pointer; }}
  .dialog-close:hover {{ background: var(--bg); color: var(--text); }}
  .prompt-text {{ flex: 1 1 auto; min-height: 0; overflow: auto; margin: 0; padding: 14px 16px; border-radius: 8px; background: var(--bg); font-size: 14px; line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }}
  .dialog-foot {{ display: flex; align-items: center; justify-content: flex-end; gap: 12px; }}
  .copy-status {{ color: var(--muted); font-size: 13px; }}
  .copy-button {{ display: inline-flex; align-items: center; gap: 8px; font: inherit; font-weight: 600; padding: 8px 16px; border-radius: 8px; border: 1px solid var(--accent); background: var(--accent); color: var(--accent-text); cursor: pointer; }}
  .copy-button:disabled {{ opacity: .5; cursor: default; }}
  @media (max-width: 600px) {{ .reference {{ flex-direction: column; }} .reference a {{ flex-basis: auto; }} .controls {{ position: static; }} }}
</style>
</head>
<body>
<header>
  <h1>Art Style References</h1>
  <p>One character, {len(styles)} styles. Filter by tag, click an image to open it at full size. Bookmark a style to save it in this browser.</p>
</header>
{reference}
<div class="controls">
  <div class="chips" id="chips" role="group" aria-label="Filter by tag"></div>
  <input type="search" id="search" placeholder="Search styles…" aria-label="Search styles">
  <button class="text-button" type="button" id="manage-collections">Collections</button>
  <div class="chips" id="collection-chips" role="group" aria-label="Filter by collection"></div>
  <p class="dialog-note" id="share-note" hidden></p>
</div>
<p class="status" id="status" aria-live="polite"></p>
<nav class="pager" id="pager-top" aria-label="Pagination"></nav>
<main id="grid"></main>
<nav class="pager" id="pager-bottom" aria-label="Pagination"></nav>
<dialog id="prompt-dialog" aria-labelledby="prompt-title">
  <div class="dialog-inner">
    <div class="dialog-head">
      <div><h2 id="prompt-title"></h2><p>Add to a reference image or to your own scene description</p></div>
      <button class="dialog-close" type="button" aria-label="Close" data-close><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
    </div>
    <div class="prompt-text" id="prompt-text" role="region" aria-label="Prompt" tabindex="0"></div>
    <div class="dialog-foot">
      <span class="copy-status" id="copy-status" role="status"></span>
      <button class="copy-button" type="button" id="copy-button"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy prompt</button>
    </div>
  </div>
</dialog>
<dialog id="picker-dialog" aria-labelledby="picker-title">
  <div class="dialog-inner">
    <div class="dialog-head">
      <div><h2 id="picker-title"></h2><p>Choose collections. Saved is the default.</p></div>
      <button class="dialog-close" type="button" aria-label="Close" data-close><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
    </div>
    <ul class="check-list" id="picker-list"></ul>
    <form class="collection-create" id="picker-create">
      <input type="text" id="picker-name" maxlength="40" placeholder="New collection" aria-label="New collection name" autocomplete="off">
      <button class="text-button" type="submit">Create and add</button>
    </form>
    <p class="io-status" id="picker-status" role="status"></p>
  </div>
</dialog>
<dialog id="manager-dialog" aria-labelledby="manager-title">
  <div class="dialog-inner">
    <div class="dialog-head">
      <div>
        <h2 id="manager-title">Collections</h2>
        <p>Stored in this browser only. Share a link, or copy the export to move them.</p>
      </div>
      <button class="dialog-close" type="button" aria-label="Close" data-close><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg></button>
    </div>
    <ul class="manager-list" id="manager-list"></ul>
    <form class="collection-create" id="manager-create">
      <input type="text" id="manager-name" maxlength="40" placeholder="New collection" aria-label="New collection name" autocomplete="off">
      <button class="text-button" type="submit">Create</button>
    </form>
    <p class="io-status" id="manager-status" role="status"></p>
    <div class="io">
      <h3>Export</h3>
      <p class="dialog-note">Each collection is its name followed by style numbers, the same numbers shown on the cards. Importing replaces the collections in that browser.</p>
      <textarea id="export-text" readonly aria-label="Export text"></textarea>
      <div class="dialog-foot">
        <span class="io-status" id="export-status" role="status"></span>
        <button class="copy-button" type="button" id="copy-export">Copy export</button>
      </div>
      <h3>Import</h3>
      <textarea id="import-text" aria-label="Import text" placeholder='[["Saved",1,42],["Noir",42]]'></textarea>
      <div class="dialog-foot">
        <span class="io-status" id="import-status" role="status"></span>
        <button class="text-button" type="button" id="do-import">Import and replace</button>
      </div>
    </div>
  </div>
</dialog>
<script type="application/json" id="data">{data}</script>
<script>
const {{ pageSize, tagLabels, promptsSrc, styles }} = JSON.parse(document.getElementById("data").textContent);
const chipsEl = document.getElementById("chips");
const searchEl = document.getElementById("search");
const gridEl = document.getElementById("grid");
const statusEl = document.getElementById("status");
const pagers = [document.getElementById("pager-top"), document.getElementById("pager-bottom")];

const state = {{ tags: new Set(), query: "", page: 1, collection: "", shared: false }};
const stylesByStem = new Map(styles.map(s => [s.stem, s]));
const styleNumbers = new Set(styles.map(s => s.n));
const collectionChipsEl = document.getElementById("collection-chips");
const promptIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M7 8h10M7 12h6"/></svg>`;
const bookmarkIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m19 21-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/></svg>`;
const plusIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 7v10M7 12h10"/></svg>`;

// Collections live only in localStorage. The stored value is the export string.
// Canonical form: [["Saved",1,42],["Noir",42,88]]
// "Saved" is the default collection. Numbers are the style ids printed on each card
// (the leading number in the filename), sorted, not the card's position in the grid.
const STORAGE_KEY = "imagestyles.collections";
const DEFAULT_COLLECTION = "Saved";
let collections = loadCollections();
// A ?shared= link is one temporary collection. It is not written to localStorage.
let sharedCollection = null;
let shareError = "";

function uniqueIds(values) {{
  const ids = [];
  for (const value of values) {{
    const n = typeof value === "number" ? value : Number(String(value).trim());
    if (Number.isInteger(n) && n > 0 && !ids.includes(n)) ids.push(n);
  }}
  ids.sort((a, b) => a - b);
  return ids;
}}

function cleanName(name) {{
  return String(name ?? "").trim().replace(/[ \\t\\n\\r]+/g, " ");
}}

function normalizeCollections(list) {{
  const out = [];
  const seen = new Set();
  for (const entry of list) {{
    const name = cleanName(entry.name);
    const key = name.toLowerCase();
    if (!name || name.length > 40 || seen.has(key)) continue;
    seen.add(key);
    out.push({{ name, ids: uniqueIds(entry.ids || []) }});
  }}
  const savedIndex = out.findIndex(c => c.name.toLowerCase() === DEFAULT_COLLECTION.toLowerCase());
  const saved = savedIndex >= 0 ? out.splice(savedIndex, 1)[0] : {{ name: DEFAULT_COLLECTION, ids: [] }};
  saved.name = DEFAULT_COLLECTION;
  out.unshift(saved);
  return out;
}}

function parseSerialized(text) {{
  const trimmed = String(text ?? "").trim();
  if (!trimmed) return [];
  if (trimmed.startsWith("[")) {{
    const data = JSON.parse(trimmed);
    if (!Array.isArray(data)) throw new Error("Export text must be a list of collections.");
    return data.map(row => {{
      if (!Array.isArray(row) || row.length < 1) throw new Error("Each collection must start with its name.");
      return {{ name: row[0], ids: row.slice(1) }};
    }});
  }}
  if (trimmed.startsWith("{{")) {{
    const data = JSON.parse(trimmed);
    if (!data || Array.isArray(data) || typeof data !== "object") throw new Error("Export text must be a list of collections.");
    return Object.entries(data).map(([name, ids]) => {{
      if (!Array.isArray(ids)) throw new Error("Collection entries must be lists of style numbers.");
      return {{ name, ids }};
    }});
  }}
  if (/^[0-9, \\t\\n\\r]+$/.test(trimmed)) return [{{ name: DEFAULT_COLLECTION, ids: trimmed.split(",") }}];
  throw new Error("Paste a collections export, or a list of style numbers like 1,42,88.");
}}

function serializeCollections(list) {{
  return JSON.stringify(list.map(c => [c.name, ...c.ids]));
}}

function loadCollections() {{
  try {{
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return normalizeCollections([]);
    return normalizeCollections(parseSerialized(raw));
  }} catch {{
    return normalizeCollections([]);
  }}
}}

function persistCollections() {{
  localStorage.setItem(STORAGE_KEY, serializeCollections(collections));
}}

function collectionByName(name) {{
  return collections.find(c => c.name === name);
}}

function activeCollection() {{
  if (state.shared && sharedCollection) return sharedCollection;
  return state.collection ? collectionByName(state.collection) : null;
}}

function encodeShare(col) {{
  const json = JSON.stringify([col.name, ...col.ids]);
  const bytes = new TextEncoder().encode(json);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}}

function decodeShare(payload) {{
  const text = String(payload ?? "").trim().replace(/ /g, "+");
  if (!text || text.length > 100000) throw new Error("bad share");
  const binary = atob(text);
  const bytes = Uint8Array.from(binary, c => c.charCodeAt(0));
  const data = JSON.parse(new TextDecoder().decode(bytes));
  if (!Array.isArray(data) || typeof data[0] !== "string") throw new Error("bad share");
  let name = cleanName(data[0]);
  if (!name) name = "Shared";
  if (name.length > 40) name = name.slice(0, 40);
  const ids = uniqueIds(data.slice(1));
  if (ids.length > 5000) throw new Error("bad share");
  return {{ name, ids }};
}}

function readShared() {{
  const raw = new URLSearchParams(location.search).get("shared");
  shareError = "";
  if (!raw) {{
    sharedCollection = null;
    state.shared = false;
    return;
  }}
  try {{
    sharedCollection = decodeShare(raw);
  }} catch {{
    sharedCollection = null;
    state.shared = false;
    shareError = "This share link could not be read.";
  }}
}}

function shareUrl(col) {{
  const url = new URL(location.href);
  url.hash = "";
  url.search = "";
  url.searchParams.set("shared", encodeShare(col));
  return url.toString();
}}

function knownCount(col) {{
  return col.ids.filter(n => styleNumbers.has(n)).length;
}}

function inCollection(n, name) {{
  const col = collectionByName(name);
  return !!col && col.ids.includes(n);
}}

function inOtherCollections(n) {{
  return collections.slice(1).some(c => c.ids.includes(n));
}}

function setMembership(n, name, on) {{
  const col = collectionByName(name);
  if (!col) return;
  const has = col.ids.includes(n);
  if (on && !has) col.ids.push(n);
  if (!on && has) col.ids = col.ids.filter(id => id !== n);
  col.ids.sort((a, b) => a - b);
}}

function nameError(name, ignoreName) {{
  const clean = cleanName(name);
  if (!clean) return "Enter a name.";
  if (clean.length > 40) return "Use 40 characters or fewer.";
  const key = clean.toLowerCase();
  if (key === DEFAULT_COLLECTION.toLowerCase() && (ignoreName || "").toLowerCase() !== key) return "Saved is the default collection.";
  if (collections.some(c => c.name !== ignoreName && c.name.toLowerCase() === key)) return "That collection already exists.";
  return "";
}}

function addCollection(name, styleNumber) {{
  const error = nameError(name);
  if (error) return error;
  const ids = styleNumber == null ? [] : [styleNumber];
  collections.push({{ name: cleanName(name), ids }});
  return "";
}}

function readHash() {{
  const params = new URLSearchParams(location.hash.slice(1));
  state.tags = new Set((params.get("tags") || "").split(",").filter(t => t in tagLabels));
  state.query = params.get("q") || "";
  state.page = Math.max(1, parseInt(params.get("page"), 10) || 1);
  const col = params.get("col") || "";
  if (collectionByName(col)) {{
    state.collection = col;
    state.shared = false;
  }} else {{
    state.collection = "";
  }}
  searchEl.value = state.query;
}}

function writeHash() {{
  const params = new URLSearchParams();
  if (state.tags.size) params.set("tags", [...state.tags].join(","));
  if (state.query) params.set("q", state.query);
  if (state.page > 1) params.set("page", state.page);
  if (state.collection) params.set("col", state.collection);
  const hash = params.toString();
  history.replaceState(null, "", hash ? "#" + hash : location.pathname + location.search);
}}

function matchesQuery(style) {{
  if (!state.query) return true;
  const q = state.query.toLowerCase();
  return style.title.toLowerCase().includes(q) || style.desc.toLowerCase().includes(q);
}}

function filtered() {{
  const selected = activeCollection();
  return styles.filter(s =>
    (!selected || selected.ids.includes(s.n)) &&
    (!state.tags.size || s.tags.some(t => state.tags.has(t))) &&
    matchesQuery(s));
}}

function renderChips() {{
  const selected = activeCollection();
  const pool = styles.filter(s => (!selected || selected.ids.includes(s.n)) && matchesQuery(s));
  const counts = {{}};
  for (const s of pool) for (const t of s.tags) counts[t] = (counts[t] || 0) + 1;
  const allCount = pool.length;
  const chip = (key, label, count, pressed) =>
    `<button class="chip" data-tag="${{key}}" aria-pressed="${{pressed}}">${{label}}<span class="count">${{count}}</span></button>`;
  chipsEl.innerHTML = chip("", "All", allCount, state.tags.size === 0) +
    Object.entries(tagLabels).map(([key, label]) => chip(key, label, counts[key] || 0, state.tags.has(key))).join("");
}}

function escapeHtml(text) {{
  return text.replace(/[&<>"]/g, c => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }}[c]));
}}

function card(s) {{
  const title = escapeHtml(s.title);
  const tags = s.tags.map(t => `<button class="tag" data-tag="${{t}}">${{tagLabels[t]}}</button>`).join("");
  const saved = inCollection(s.n, DEFAULT_COLLECTION);
  const promptButton = s.hasPrompt
    ? `<button class="prompt-button" type="button" data-stem="${{s.stem}}" aria-label="Show style prompt for ${{title}}" title="Style prompt">${{promptIcon}}</button>`
    : "";
  const saveLabel = saved ? `Remove ${{title}} from Saved` : `Save ${{title}}`;
  return `<figure>
    <a href="${{s.file}}" target="_blank"><img src="${{s.thumb}}" alt="${{title}}" width="512" height="512" loading="lazy" decoding="async"></a>
    <div class="save-control">
      <button class="save-button" type="button" data-n="${{s.n}}" aria-pressed="${{saved}}" aria-label="${{saveLabel}}" title="${{saved ? "Remove from Saved" : "Save"}}">${{bookmarkIcon}}</button>
      <button class="save-more" type="button" data-n="${{s.n}}" aria-haspopup="dialog" aria-label="Choose collections for ${{title}}" title="Collections"${{inOtherCollections(s.n) ? ' data-collected="true"' : ""}}>${{plusIcon}}</button>
    </div>
    ${{promptButton}}
    <figcaption><strong>${{s.n}}. ${{title}}</strong><span class="desc">${{escapeHtml(s.desc)}}</span><div class="tags">${{tags}}</div></figcaption>
  </figure>`;
}}

function renderCollectionChips() {{
  const local = collections.map(c => {{
    const pressed = !state.shared && state.collection === c.name;
    return `<button class="chip" type="button" data-collection="${{escapeHtml(c.name)}}" aria-pressed="${{pressed}}">${{escapeHtml(c.name)}}<span class="count">${{knownCount(c)}}</span></button>`;
  }}).join("");
  let shared = "";
  if (sharedCollection) {{
    const clash = collections.some(c => c.name.toLowerCase() === sharedCollection.name.toLowerCase());
    const label = escapeHtml(clash ? `${{sharedCollection.name}} (link)` : sharedCollection.name);
    shared = `<button class="chip" type="button" data-shared="true" aria-pressed="${{state.shared}}" title="From this link. Not saved in this browser.">${{label}}<span class="count">${{knownCount(sharedCollection)}}</span></button>`;
  }}
  collectionChipsEl.innerHTML = local + shared;
}}

function renderShareNote() {{
  const note = document.getElementById("share-note");
  if (shareError) {{
    note.hidden = false;
    note.textContent = shareError;
  }} else if (state.shared && sharedCollection) {{
    note.hidden = false;
    note.textContent = `“${{sharedCollection.name}}” is open from this link and is not saved in this browser.`;
  }} else {{
    note.hidden = true;
    note.textContent = "";
  }}
}}

function renderPager(pageCount) {{
  const html = pageCount <= 1 ? "" :
    `<button data-page="${{state.page - 1}}" ${{state.page === 1 ? "disabled" : ""}} aria-label="Previous page">‹</button>` +
    Array.from({{ length: pageCount }}, (_, i) => i + 1).map(p =>
      `<button data-page="${{p}}" ${{p === state.page ? 'aria-current="page"' : ""}}>${{p}}</button>`).join("") +
    `<button data-page="${{state.page + 1}}" ${{state.page === pageCount ? "disabled" : ""}} aria-label="Next page">›</button>`;
  for (const pager of pagers) pager.innerHTML = html;
}}

function render() {{
  const items = filtered();
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  state.page = Math.min(state.page, pageCount);
  const start = (state.page - 1) * pageSize;
  const pageItems = items.slice(start, start + pageSize);

  renderChips();
  renderCollectionChips();
  renderShareNote();
  renderPager(pageCount);
  const selected = activeCollection();
  const empty = selected
    ? `Nothing in ${{escapeHtml(selected.name)}} matches this filter.`
    : "No styles match this filter.";
  gridEl.innerHTML = pageItems.length ? pageItems.map(card).join("") : `<p class="empty">${{empty}}</p>`;
  const where = selected ? ` in ${{selected.name}}` : "";
  statusEl.textContent = items.length
    ? `Showing ${{start + 1}}–${{start + pageItems.length}} of ${{items.length}} styles${{where}}` + (pageCount > 1 ? ` · page ${{state.page}} of ${{pageCount}}` : "")
    : "";
  writeHash();
}}

function toggleTag(tag) {{
  if (!tag) state.tags.clear();
  else if (state.tags.has(tag)) state.tags.delete(tag);
  else state.tags.add(tag);
  state.page = 1;
  render();
}}

chipsEl.addEventListener("click", e => {{
  const chip = e.target.closest(".chip");
  if (chip) toggleTag(chip.dataset.tag);
}});

const dialogEl = document.getElementById("prompt-dialog");
const promptTitleEl = document.getElementById("prompt-title");
const promptTextEl = document.getElementById("prompt-text");
const copyButton = document.getElementById("copy-button");
const copyStatusEl = document.getElementById("copy-status");
let promptsPromise;
let copyStatusTimer;

function loadPrompts() {{
  promptsPromise ||= new Promise((resolve, reject) => {{
    const script = document.createElement("script");
    script.src = promptsSrc;
    script.onload = () => resolve(window.stylePrompts);
    script.onerror = () => {{ promptsPromise = null; script.remove(); reject(new Error("Could not load prompts")); }};
    document.head.append(script);
  }});
  return promptsPromise;
}}

async function openPrompt(stem) {{
  const style = stylesByStem.get(stem);
  dialogEl.dataset.stem = stem;
  promptTitleEl.textContent = `${{style.n}}. ${{style.title}}`;
  promptTextEl.textContent = "Loading prompt…";
  copyButton.disabled = true;
  copyStatusEl.textContent = "";
  dialogEl.showModal();
  try {{
    const prompts = await loadPrompts();
    if (dialogEl.dataset.stem !== stem) return;
    promptTextEl.textContent = prompts[stem];
    copyButton.disabled = false;
  }} catch {{
    if (dialogEl.dataset.stem === stem) promptTextEl.textContent = "The prompt couldn't be loaded. Check your connection and try again.";
  }}
}}

async function copyText(text) {{
  try {{
    await navigator.clipboard.writeText(text);
  }} catch {{
    const area = Object.assign(document.createElement("textarea"), {{ value: text }});
    dialogEl.append(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    if (!copied) throw new Error("Copy failed");
  }}
}}

copyButton.addEventListener("click", async () => {{
  clearTimeout(copyStatusTimer);
  try {{
    await copyText(promptTextEl.textContent);
    copyStatusEl.textContent = "Copied to clipboard";
  }} catch {{
    copyStatusEl.textContent = "Copy failed. Select the text and copy it manually.";
  }}
  copyStatusTimer = setTimeout(() => {{ copyStatusEl.textContent = ""; }}, 2500);
}});

dialogEl.addEventListener("click", e => {{
  if (e.target === dialogEl || e.target.closest("[data-close]")) dialogEl.close();
}});

// Start loading prompts as soon as someone reaches for a prompt button.
for (const type of ["pointerover", "focusin"]) gridEl.addEventListener(type, e => {{
  if (e.target.closest(".prompt-button")) loadPrompts().catch(() => {{}});
}});

function paintCard(n) {{
  const style = styles.find(s => s.n === n);
  const title = style ? style.title : String(n);
  for (const button of gridEl.querySelectorAll(`.save-button[data-n="${{n}}"]`)) {{
    const saved = inCollection(n, DEFAULT_COLLECTION);
    button.setAttribute("aria-pressed", String(saved));
    button.title = saved ? "Remove from Saved" : "Save";
    button.setAttribute("aria-label", saved ? `Remove ${{title}} from Saved` : `Save ${{title}}`);
  }}
  for (const button of gridEl.querySelectorAll(`.save-more[data-n="${{n}}"]`)) {{
    if (inOtherCollections(n)) button.dataset.collected = "true";
    else delete button.dataset.collected;
  }}
}}

function afterMembershipChange(n) {{
  try {{
    persistCollections();
  }} catch {{
    statusEl.textContent = "Couldn't save collections in this browser.";
    return;
  }}
  const selected = activeCollection();
  if (selected && !state.shared && !selected.ids.includes(n)) render();
  else {{
    paintCard(n);
    renderCollectionChips();
    writeHash();
  }}
}}

gridEl.addEventListener("click", e => {{
  const saveButton = e.target.closest(".save-button");
  if (saveButton) {{
    const n = Number(saveButton.dataset.n);
    setMembership(n, DEFAULT_COLLECTION, !inCollection(n, DEFAULT_COLLECTION));
    afterMembershipChange(n);
    if (pickerDialog.open && pickerN === n) renderPickerChecks();
    return;
  }}
  const moreButton = e.target.closest(".save-more");
  if (moreButton) {{
    openPicker(Number(moreButton.dataset.n));
    return;
  }}
  const promptButton = e.target.closest(".prompt-button");
  if (promptButton) {{
    openPrompt(promptButton.dataset.stem);
    return;
  }}
  const tag = e.target.closest(".tag");
  if (!tag) return;
  state.tags = new Set([tag.dataset.tag]);
  state.page = 1;
  render();
  window.scrollTo({{ top: chipsEl.getBoundingClientRect().top + scrollY - 16, behavior: "smooth" }});
}});

collectionChipsEl.addEventListener("click", e => {{
  if (e.target.closest("[data-shared]")) {{
    state.shared = !state.shared;
    if (state.shared) state.collection = "";
    state.page = 1;
    render();
    return;
  }}
  const chip = e.target.closest("[data-collection]");
  if (!chip) return;
  const name = chip.dataset.collection;
  state.collection = !state.shared && state.collection === name ? "" : name;
  state.shared = false;
  state.page = 1;
  render();
}});

const pickerDialog = document.getElementById("picker-dialog");
const pickerTitle = document.getElementById("picker-title");
const pickerList = document.getElementById("picker-list");
const pickerCreate = document.getElementById("picker-create");
const pickerName = document.getElementById("picker-name");
const pickerStatus = document.getElementById("picker-status");
let pickerN = null;

function renderPickerChecks() {{
  pickerList.innerHTML = collections.map(c => {{
    const on = c.ids.includes(pickerN);
    return `<li><label><input type="checkbox" data-collection="${{escapeHtml(c.name)}}"${{on ? " checked" : ""}}> ${{escapeHtml(c.name)}}</label></li>`;
  }}).join("");
}}

function openPicker(n) {{
  const style = styles.find(s => s.n === n);
  pickerN = n;
  pickerTitle.textContent = style ? `${{style.n}}. ${{style.title}}` : String(n);
  pickerName.value = "";
  pickerStatus.textContent = "";
  renderPickerChecks();
  pickerDialog.showModal();
}}

pickerList.addEventListener("change", e => {{
  const box = e.target.closest('input[type="checkbox"]');
  if (!box || pickerN == null) return;
  setMembership(pickerN, box.dataset.collection, box.checked);
  afterMembershipChange(pickerN);
}});

pickerCreate.addEventListener("submit", e => {{
  e.preventDefault();
  const error = addCollection(pickerName.value, pickerN);
  pickerStatus.textContent = error;
  if (error) return;
  pickerName.value = "";
  renderPickerChecks();
  afterMembershipChange(pickerN);
}});

pickerDialog.addEventListener("click", e => {{
  if (e.target === pickerDialog || e.target.closest("[data-close]")) pickerDialog.close();
}});

const managerDialog = document.getElementById("manager-dialog");
const managerList = document.getElementById("manager-list");
const managerCreate = document.getElementById("manager-create");
const managerName = document.getElementById("manager-name");
const exportText = document.getElementById("export-text");
const exportStatus = document.getElementById("export-status");
const importText = document.getElementById("import-text");
const importStatus = document.getElementById("import-status");
const managerStatus = document.getElementById("manager-status");
const copyExport = document.getElementById("copy-export");
let ioTimer;

function renderManager() {{
  exportText.value = serializeCollections(collections);
  managerList.innerHTML = collections.map(c => {{
    const count = `${{knownCount(c)}} style${{knownCount(c) === 1 ? "" : "s"}}`;
    if (c.name === DEFAULT_COLLECTION) {{
      return `<li class="manager-item" data-name="Saved"><span class="name">Saved</span><span class="meta">${{count}} · default</span><button class="small-button" type="button" data-share>Share</button></li>`;
    }}
    const name = escapeHtml(c.name);
    return `<li class="manager-item" data-name="${{name}}"><input type="text" value="${{name}}" maxlength="40" aria-label="Rename ${{name}}"><span class="meta">${{count}}</span><button class="small-button" type="button" data-share>Share</button><button class="small-button" type="button" data-rename>Rename</button><button class="danger" type="button" data-delete>Delete</button></li>`;
  }}).join("");
}}

function openManager() {{
  managerName.value = "";
  managerStatus.textContent = "";
  exportStatus.textContent = "";
  importStatus.textContent = "";
  importText.value = "";
  renderManager();
  managerDialog.showModal();
}}

document.getElementById("manage-collections").addEventListener("click", openManager);

managerCreate.addEventListener("submit", e => {{
  e.preventDefault();
  managerStatus.textContent = addCollection(managerName.value, null);
  if (managerStatus.textContent) return;
  managerName.value = "";
  persistCollections();
  render();
  renderManager();
}});

managerList.addEventListener("click", async e => {{
  const item = e.target.closest(".manager-item");
  if (!item) return;
  const current = item.dataset.name;
  if (e.target.closest("[data-share]")) {{
    const col = collectionByName(current);
    if (!col) return;
    const url = shareUrl(col);
    clearTimeout(ioTimer);
    try {{
      await copyText(url);
      managerStatus.textContent = "Share link copied.";
      ioTimer = setTimeout(() => {{ managerStatus.textContent = ""; }}, 2500);
    }} catch {{
      managerStatus.textContent = url;
    }}
    return;
  }}
  if (e.target.closest("[data-delete]")) {{
    if (!confirm(`Delete the collection “${{current}}”? Styles in other collections stay there.`)) return;
    collections = collections.filter(c => c.name !== current);
    if (state.collection === current) state.collection = "";
    persistCollections();
    render();
    renderManager();
    return;
  }}
  if (!e.target.closest("[data-rename]")) return;
  const next = cleanName(item.querySelector("input").value);
  if (next === current) return;
  const error = nameError(next, current);
  managerStatus.textContent = error;
  if (error) return;
  collectionByName(current).name = next;
  if (state.collection === current) state.collection = next;
  persistCollections();
  render();
  renderManager();
}});

copyExport.addEventListener("click", async () => {{
  clearTimeout(ioTimer);
  try {{
    await copyText(exportText.value);
    exportStatus.textContent = "Copied to clipboard";
  }} catch {{
    exportStatus.textContent = "Copy failed. Select the text and copy it manually.";
  }}
  ioTimer = setTimeout(() => {{ exportStatus.textContent = ""; }}, 2500);
}});

document.getElementById("do-import").addEventListener("click", () => {{
  if (!importText.value.trim()) {{
    importStatus.textContent = "Paste an export first.";
    return;
  }}
  try {{
    const next = normalizeCollections(parseSerialized(importText.value));
    collections = next;
    if (state.collection && !collectionByName(state.collection)) state.collection = "";
    persistCollections();
    importText.value = "";
    importStatus.textContent = "Imported. The collections in this browser were replaced.";
    render();
    renderManager();
    if (pickerDialog.open && pickerN != null) renderPickerChecks();
  }} catch (error) {{
    importStatus.textContent = error.message || "That text could not be imported.";
  }}
}});

managerDialog.addEventListener("click", e => {{
  if (e.target === managerDialog || e.target.closest("[data-close]")) managerDialog.close();
}});

for (const pager of pagers) pager.addEventListener("click", e => {{
  const button = e.target.closest("button[data-page]");
  if (!button || button.disabled) return;
  state.page = parseInt(button.dataset.page, 10);
  render();
  gridEl.scrollIntoView({{ behavior: "smooth", block: "start" }});
}});

let searchTimer;
searchEl.addEventListener("input", () => {{
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {{ state.query = searchEl.value.trim(); state.page = 1; render(); }}, 150);
}});

window.addEventListener("hashchange", () => {{ readHash(); render(); }});
window.addEventListener("popstate", () => {{
  readShared();
  readHash();
  if (sharedCollection && !state.collection) state.shared = true;
  render();
}});
readShared();
readHash();
if (sharedCollection && !state.collection) state.shared = true;
render();
</script>
</body>
</html>
"""

out_dir.mkdir(exist_ok=True)
(out_dir / "index.html").write_text(page)
(out_dir / "prompts.js").write_text(prompts_js)
print(f"wrote {out_dir.relative_to(set_dir.parent)}/index.html ({len(styles)} styles, {sum(s['hasPrompt'] for s in styles)} prompts)")

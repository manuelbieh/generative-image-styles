#!/usr/bin/env python3
"""Recover the exact image prompt behind every style image from the Codex session logs.

Codex records each image generation as an `image_gen.generation` item (revisedPrompt + savedPath)
and each copy into the set as a CommandExecution (`sips ... <savedPath> --out styles/<stem>.png`).
The last copy to a stem wins, so retries and replacements resolve to the image on disk.

Every mapping is checked against the pixels: a 16x16 grayscale fingerprint of the generated
image must match the style PNG. Styles whose copy command can't be parsed (variables, two-hop
copies through temp files) fall back to the closest-looking generation from the sessions that
touched that style.

Usage: extract-prompts.py [set-dir]  -> writes <set-dir>/prompts.json as {stem: prompt}
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from pathlib import Path

set_name = sys.argv[1] if len(sys.argv) > 1 else "set-2"
set_dir = Path(__file__).parent / set_name
sessions = sorted((Path.home() / ".codex/sessions").glob("*/*/*/*.jsonl"))

SAVED_RE = re.compile(r"/[^\s'\"\\]*/\.codex/generated_images/[^\s'\"\\]+\.png")
TARGET_RE = re.compile(r"\b(\d+-[a-z0-9-]+)\.png")
TEMP_RE = re.compile(r"[\w./-]+\.(?:png|jpe?g|webp)\b")
# Mean absolute difference (0-255) of the fingerprints. Plain resizes score below 4;
# padding, letterboxing and background cleanup reach about 35.
MATCH_WARN_DISTANCE = 4

stems = {line.split("\t")[0] for line in (set_dir / "styles.tsv").read_text().splitlines() if line.strip()}


def copy_pairs(command):
    """Yield (stem, saved path) pairs from a shell command or inline script.

    Handles `sips <saved> --out styles/<stem>.png` lines as well as scripts carrying
    [{"file": "<stem>.png", "source": "<saved>"}, ...] lists, by pairing both kinds of
    paths in order whenever a chunk has as many of one as the other. Chunks go from finest
    (single statements) to coarsest (the whole command); the finest match for a stem wins.
    """
    paired = set()
    for chunks in (re.split(r"\n|&&|;", command), command.split("\n"), [command]):
        for chunk in chunks:
            saved = SAVED_RE.findall(chunk)
            targets = [t for t in TARGET_RE.findall(chunk) if t in stems]
            if saved and len(saved) == len(targets):
                for stem, path in zip(targets, saved):
                    if stem not in paired:
                        paired.add(stem)
                        yield stem, path


def temp_copies(command, aliases):
    """Yield (stem, saved path) for two-hop copies: <saved> -> temp file -> styles/<stem>.png.

    `aliases` maps temp file names to the generated image they were exported from; it is
    filled here and must persist across the commands of one session.
    """
    for statement in re.split(r"\n|&&|;", command):
        saved = SAVED_RE.findall(statement)
        others = [Path(p).name for p in TEMP_RE.findall(SAVED_RE.sub("", statement))]
        others = [name for name in others if Path(name).stem not in stems]
        targets = [t for t in TARGET_RE.findall(statement) if t in stems]
        if len(saved) == 1 and len(others) == 1 and not targets:
            aliases[others[0]] = saved[0]
        elif not saved and len(others) == 1 and len(targets) == 1 and others[0] in aliases:
            yield targets[0], aliases[others[0]]


@cache
def fingerprint(path):
    raw = subprocess.run(["magick", str(path), "-resize", "16x16!", "-colorspace", "Gray", "-depth", "8", "gray:-"],
                         capture_output=True, check=True).stdout
    return raw


def distance(a, b):
    fa, fb = fingerprint(a), fingerprint(b)
    return sum(abs(x - y) for x, y in zip(fa, fb)) / len(fa)


def style_png(stem):
    return set_dir / "styles" / f"{stem}.png"


prompts_by_path = {}
copies = []  # (timestamp, stem, saved path)
session_generations = defaultdict(list)  # stem -> saved paths from sessions that mention the stem

for session in sessions:
    with session.open() as fh:
        lines = [line for line in fh if '"item_completed"' in line
                 and ('"image_gen.generation"' in line or '"CommandExecution"' in line)]
    if not any("dev/gpt-images" in line for line in lines):
        continue
    generated = []
    mentioned = set()
    aliases = {}
    for line in lines:
        entry = json.loads(line)
        item = entry["payload"]["item"]
        if item.get("kind") == "image_gen.generation":
            if item.get("status") == "completed" and item.get("savedPath"):
                prompts_by_path[item["savedPath"]] = item["revisedPrompt"]
                generated.append(item["savedPath"])
            continue
        if item.get("type") != "CommandExecution" or item.get("exit_code") != 0:
            continue
        command = item["command"][-1] if isinstance(item["command"], list) else item["command"]
        mentioned.update(t for t in TARGET_RE.findall(command) if t in stems)
        for stem, saved in [*copy_pairs(command), *temp_copies(command, aliases)]:
            copies.append((entry["timestamp"], stem, saved))
    for stem in mentioned:
        session_generations[stem].extend(generated)

sources = {}
for _, stem, saved in sorted(copies):
    if saved in prompts_by_path:
        sources[stem] = saved

on_disk = sorted((s for s in stems if style_png(s).exists()), key=lambda s: int(s.split("-")[0]))
warnings = []


def resolve(stem):
    candidates = [p for p in session_generations[stem] if Path(p).exists()]
    source = sources.get(stem)
    if source and Path(source).exists():
        score = distance(style_png(stem), source)
        if score < MATCH_WARN_DISTANCE:
            return stem, source, None
        # Heavy post-processing (letterboxing, padding) also scores high, so only a clear match overrides the log.
        best = min(candidates, key=lambda p: distance(style_png(stem), p), default=source)
        if best != source and distance(style_png(stem), best) < MATCH_WARN_DISTANCE:
            return stem, best, f"{stem}: log says {Path(source).name}, pixels match {Path(best).name}"
        return stem, source, None
    if source:
        return stem, source, None
    if not candidates:
        candidates = [p for p in prompts_by_path if Path(p).exists()]
    if not candidates:
        return stem, None, None
    best = min(candidates, key=lambda p: distance(style_png(stem), p))
    score = distance(style_png(stem), best)
    note = f"{stem}: matched by pixels only (distance {score:.1f})" if score >= MATCH_WARN_DISTANCE else None
    return stem, best, note


# Start from the previous run so prompts survive Codex cleaning up old sessions or generated images.
prompts_file = set_dir / "prompts.json"
previous = json.loads(prompts_file.read_text()) if prompts_file.exists() else {}
prompts = {stem: previous[stem] for stem in on_disk if stem in previous}
with ThreadPoolExecutor(max_workers=12) as pool:
    for stem, source, note in pool.map(resolve, on_disk):
        if source:
            prompts[stem] = prompts_by_path[source]
        if note:
            warnings.append(note)

prompts = {stem: prompts[stem] for stem in on_disk if stem in prompts}
prompts_file.write_text(json.dumps(prompts, ensure_ascii=False, indent=1) + "\n")
print(f"wrote {set_name}/prompts.json ({len(prompts)} of {len(on_disk)} styles)")
missing = [stem for stem in on_disk if stem not in prompts]
if missing:
    print("  no prompt found for: " + " ".join(missing))
for note in warnings:
    print("  " + note)

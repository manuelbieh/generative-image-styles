#!/bin/zsh
# Usage: run-batch.sh <start-line> <count>
cd "$(dirname "$0")"
batch=$(sed -n "$1,$(( $1 + $2 - 1 ))p" styles.tsv | awk -F'\t' '{printf "- ./styles/%s.png : %s\n", $1, $2}')
codex exec -s workspace-write --skip-git-repo-check -i base.png - <<PROMPT
The attached image is a reference photo of a woman in a cafe. Use your image generation tool to re-create this exact scene in each of the art styles listed below — one separate image per style, 1024x1024 square.

For every image keep the same composition and the same character identity: curly auburn shoulder-length hair, freckles, round tortoiseshell glasses, mustard-yellow knit sweater, holding a coffee cup with both hands, looking out the window, croissant and potted plant on the table. Fully commit to the target style (medium, line work, palette, rendering) — it must not look like a filter over the photo. No text, captions, signatures or watermarks.

If a request is refused because it names a specific artist or franchise, retry with a purely descriptive wording of the visual style.

Save each result to the exact path given (convert to PNG and resize to 1024x1024 with sips if needed). Do not skip any. At the end, list the files you saved.

$batch
PROMPT

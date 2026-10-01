#!/bin/zsh
# Usage: run-batch.sh <start-line> <count>
cd "$(dirname "$0")"
batch=$(sed -n "$1,$(( $1 + $2 - 1 ))p" styles.tsv | awk -F'\t' '{printf "- ./styles/%s.png : %s\n", $1, $3}')
codex exec -s workspace-write --skip-git-repo-check - <<PROMPT
Use your image generation tool to create one image per style listed below, 1024x1024 square. Do NOT use any reference image — generate each one fresh from text.

Character (the only constant): a woman in her early 30s with curly auburn shoulder-length hair, freckles, round tortoiseshell glasses and a mustard-yellow knit sweater, enjoying a coffee (croissant nearby).

The style is the priority, not the photo. For each image, let the style fully dictate proportions, anatomy, framing, camera angle, pose, setting details, color palette, lighting and medium — exactly as an authentic piece in that style would look. Do not make it look like a photo with a filter, and do not keep a common composition across images: vary the framing (close-up, full body, wide scene, profile, etc.) to whatever suits each style best. The images should look radically different from each other. No text, captions, signatures or watermarks.

If a request is refused because it names a specific artist or franchise, retry with a purely descriptive wording of the visual style.

Save each result to the exact path given (convert to PNG and resize to 1024x1024 with sips if needed). Do not skip any. At the end, list the files you saved.

$batch
PROMPT

#!/bin/zsh
# Builds an 8x6 labeled contact sheet from styles/*.png -> style-grid.jpg
cd "$(dirname "$0")"
mkdir -p .labeled
rm -f .labeled/*.png
while IFS=$'\t' read -r name desc; do
  src="styles/$name.png"
  [[ -f "$src" ]] || { echo "missing: $name"; continue; }
  label=$(echo "$name" | sed -E 's/^([0-9]+)-/\1  /; s/-/ /g')
  magick "$src" -resize 512x512^ -gravity center -extent 512x512 \
    -background '#111' -fill white -font /System/Library/Fonts/Supplemental/Arial\ Bold.ttf -pointsize 26 \
    -gravity south -splice 0x44 -annotate +0+8 "$label" ".labeled/$name.png"
done < styles.tsv
montage .labeled/*.png -tile 8x -geometry +6+6 -background '#111' style-grid.jpg
magick style-grid.jpg -quality 88 style-grid.jpg
magick identify style-grid.jpg

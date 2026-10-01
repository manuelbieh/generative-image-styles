#!/bin/zsh
# Usage: make-dist.sh <set-dir>  -> builds <set-dir>/dist with web-optimized images for deployment
set -e
cd "$(dirname "$0")/${1:-set-2}"
mkdir -p dist/thumbs dist/full
for src in styles/*.png; do
  stem=${${src:t}:r}
  [[ dist/thumbs/$stem.webp -nt $src ]] || magick "$src" -resize 512x512 -quality 80 "dist/thumbs/$stem.webp"
  [[ dist/full/$stem.jpg -nt $src ]] || magick "$src" -resize 1024x1024 -quality 85 -strip "dist/full/$stem.jpg"
done
[[ -f reference.png ]] && magick reference.png -resize 1024x1024 -quality 85 -strip dist/reference.jpg
python3 ../extract-prompts.py "${1:-set-2}"
python3 ../make-index.py "${1:-set-2}" --dist
python3 ../make-og.py "${1:-set-2}"
du -sh dist

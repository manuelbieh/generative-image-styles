#!/bin/zsh
# Usage: make-index.sh <set-dir>  -> writes <set-dir>/index.html from <set-dir>/styles.tsv
exec python3 "$(dirname "$0")/make-index.py" "${1:-set-2}"

#!/usr/bin/env bash
# Brand fonts (SIL Open Font License) pulled from the Google Fonts repo at build time.
set -euo pipefail
cd "$(dirname "$0")/../assets/fonts"
base=https://raw.githubusercontent.com/google/fonts/main/ofl
curl -sSfL "$base/jost/Jost%5Bwght%5D.ttf" -o Jost.ttf
curl -sSfL "$base/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf" -o PlayfairDisplay.ttf
curl -sSfL "$base/playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf" -o PlayfairDisplay-Italic.ttf
echo "fonts ready"

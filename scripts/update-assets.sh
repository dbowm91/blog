#!/bin/bash
# Update vendored assets from CDNs (marked.js)
#
# Prism is not vendored: it is an npm dependency built through Vite as
# `app/static/js/prism.js`. Run `npm install && npm run build` to refresh it.

set -e

ASSETS_DIR="app/static/js/lib"
mkdir -p "$ASSETS_DIR"

# Update marked.js
curl -sL https://cdn.jsdelivr.net/npm/marked/marked.min.js -o "$ASSETS_DIR/marked.min.js"

echo "Assets updated successfully"

#!/bin/bash
# Update assets from CDNs (marked.js, Prism.js)

set -e

ASSETS_DIR="app/static/js/lib"
mkdir -p "$ASSETS_DIR"

# Update marked.js
curl -sL https://cdn.jsdelivr.net/npm/marked/marked.min.js -o "$ASSETS_DIR/marked.min.js"

# Update Prism.js
curl -sL https://cdn.jsdelivr.net/npm/prismjs/prism.min.js -o "$ASSETS_DIR/prism.min.js"
curl -sL https://cdn.jsdelivr.net/npm/prismjs/components/prism-ruby.min.js -o "$ASSETS_DIR/prism-ruby.min.js"
curl -sL https://cdn.jsdelivr.net/npm/prismjs/components/prism-swift.min.js -o "$ASSETS_DIR/prism-swift.min.js"

echo "Assets updated successfully"

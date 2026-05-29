#!/usr/bin/env python3
"""Asset minification script for blog static files.

This script performs basic CSS and JS minification by removing:
- Whitespace and comments from CSS
- Whitespace and comments from JS

For production use, consider using proper tools like esbuild, terser, or cssnano.

Usage:
    python scripts/build_assets.py           # Minify all assets
    python scripts/build_assets.py --watch  # Watch mode (not implemented)
"""

import re
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
STATIC_DIR = PROJECT_ROOT / "app" / "static"
CSS_DIR = STATIC_DIR / "css"
JS_DIR = STATIC_DIR / "js"


def minify_css(content: str) -> str:
    """Remove whitespace and comments from CSS."""
    # Remove comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove unnecessary whitespace
    content = re.sub(r"\s+", " ", content)
    # Remove spaces around special characters
    content = re.sub(r"\s*([{}:;,>+~])\s*", r"\1", content)
    # Remove trailing semicolons before closing braces
    content = re.sub(r";\s*}", "}", content)
    # Remove empty rules
    content = re.sub(r"[^{}]*\s*{\s*}", "", content)
    return content.strip()


def minify_js(content: str) -> str:
    """Remove whitespace and comments from JS (basic)."""
    # Remove comments
    content = re.sub(r"//.*?$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # Remove unnecessary whitespace
    content = re.sub(r"\s+", " ", content)
    return content.strip()


def process_file(filepath: Path, minifier) -> bool:
    """Process a single file with the given minifier."""
    try:
        original_content = filepath.read_text(encoding="utf-8")
        minified_content = minifier(original_content)

        # Only write if content changed
        if minified_content != original_content:
            backup_path = filepath.with_suffix(filepath.suffix + ".orig")
            if not backup_path.exists():
                backup_path.write_text(original_content, encoding="utf-8")
            filepath.write_text(minified_content, encoding="utf-8")
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False
    return False


def main():
    parser = argparse.ArgumentParser(description="Minify static assets")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be minified")
    parser.add_argument("--force", action="store_true", help="Overwrite original files")
    args = parser.parse_args()

    if args.dry_run:
        print("Files that would be minified:")
        for css_file in CSS_DIR.glob("*.css"):
            if not css_file.name.endswith(".min.css"):
                print(f"  CSS: {css_file.relative_to(PROJECT_ROOT)}")
        for js_file in JS_DIR.glob("*.js"):
            if not js_file.name.endswith(".min.js"):
                print(f"  JS: {js_file.relative_to(PROJECT_ROOT)}")
        return

    print("Minifying assets...")

    css_count = 0
    for css_file in CSS_DIR.glob("*.css"):
        if not css_file.name.endswith(".min.css"):
            if process_file(css_file, minify_css):
                print(f"  Minified: {css_file.name}")
                css_count += 1

    js_count = 0
    for js_file in JS_DIR.glob("*.js"):
        if not js_file.name.endswith(".min.js"):
            if process_file(js_file, minify_js):
                print(f"  Minified: {js_file.name}")
                js_count += 1

    print(f"Done! Minified {css_count} CSS files and {js_count} JS files.")
    print("\nOriginal files preserved with .orig extension.")


if __name__ == "__main__":
    main()

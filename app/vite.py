"""Vite integration for content-hashed static assets."""

import hashlib
import json
from pathlib import Path

_manifest_cache = None
_manifest_path = Path(__file__).parent / "static" / "dist" / ".vite" / "manifest.json"
_css_hash_cache = {}


def get_manifest():
    """Load and cache the Vite manifest file."""
    global _manifest_cache
    if _manifest_cache is None:
        if _manifest_path.exists():
            with open(_manifest_path) as f:
                _manifest_cache = json.load(f)
        else:
            _manifest_cache = {}
    return _manifest_cache


def get_file_hash(filepath):
    """Calculate MD5 hash of file content for cache busting."""
    if filepath in _css_hash_cache:
        return _css_hash_cache[filepath]
    
    full_path = Path(__file__).parent / "static" / filepath
    if full_path.exists():
        content = full_path.read_bytes()
        file_hash = hashlib.md5(content).hexdigest()[:8]
        _css_hash_cache[filepath] = file_hash
        return file_hash
    return None


def vite_asset(url):
    """Get the content-hashed URL for a static asset.
    
    In development, returns the URL as-is (Vite dev server handles it).
    In production:
    - For JS: Looks up the hashed filename from the manifest.
    - For CSS/other: Appends content hash as query string.
    """
    manifest = get_manifest()
    
    # Normalize the URL path (remove /static/ prefix if present)
    if url.startswith("/"):
        url = url[1:]
    if url.startswith("static/"):
        url = url[len("static/"):]
    
    # Look up in manifest (for JS files processed by Vite)
    if url in manifest:
        hashed_path = manifest[url].get("file", url)
        return f"/static/dist/{hashed_path}"
    
    # For non-JS files, append content hash as query string
    file_hash = get_file_hash(url)
    if file_hash:
        return f"/static/{url}?v={file_hash}"
    
    # Fallback: return original URL
    return f"/static/{url}"


def init_vite(app):
    """Initialize Vite integration with Flask app."""
    app.jinja_env.globals["vite_asset"] = vite_asset

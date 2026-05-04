"""Vite integration for content-hashed static assets."""

import hashlib
import json
from pathlib import Path
from typing import Optional
from flask import Flask

from app.config import CDN_URL


_manifest_cache: Optional[dict] = None
_manifest_path = Path(__file__).parent / "static" / "dist" / ".vite" / "manifest.json"
_css_hash_cache: dict[str, str] = {}

def _get_base_url() -> str:
    """Get the base URL for static assets, respecting CDN_URL if configured."""
    return CDN_URL if CDN_URL else ""


def get_manifest() -> dict:
    """Load and cache the Vite manifest file."""
    global _manifest_cache
    if _manifest_cache is None:
        if _manifest_path.exists():
            with open(_manifest_path) as f:
                _manifest_cache = json.load(f)
        else:
            _manifest_cache = {}
    return _manifest_cache


def get_file_hash(filepath: str) -> Optional[str]:
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


def vite_asset(url: str) -> str:
    """Get the content-hashed URL for a static asset.
    
    In development, returns the URL as-is (Vite dev server handles it).
    In production:
    - For JS: Looks up the hashed filename from the manifest.
    - For CSS/other: Appends content hash as query string.
    
    If CDN_URL is configured, prepends it to the asset URL.
    """
    manifest = get_manifest()
    base = _get_base_url()
    
    # Normalize the URL path (remove /static/ prefix if present)
    if url.startswith("/"):
        url = url[1:]
    if url.startswith("static/"):
        url = url[len("static/"):]
    
    # Look up in manifest (for JS files processed by Vite)
    if url in manifest:
        hashed_path = manifest[url].get("file", url)
        return f"{base}/static/dist/{hashed_path}"
    
    # For non-JS files, append content hash as query string
    file_hash = get_file_hash(url)
    if file_hash:
        return f"{base}/static/{url}?v={file_hash}"
    
    # Fallback: return original URL
    return f"{base}/static/{url}"


def init_vite(app: Flask) -> None:
    """Initialize Vite integration with Flask app."""
    app.jinja_env.globals["vite_asset"] = vite_asset

"""DevLog CLI — operator interface for DevLog blog CMS."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("devlog")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

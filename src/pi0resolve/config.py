"""Load YAML configuration files."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "default.yaml"


def repo_path(relative):
    """Absolute path for a path written relative to the repository root."""
    return REPO_ROOT / relative


def load_config(path=None):
    """Return the configuration at `path` (default: configs/default.yaml) as a dict."""
    path = Path(path) if path is not None else DEFAULT_CONFIG
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

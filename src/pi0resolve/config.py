"""Load YAML configuration files."""

from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "configs" / "default.yaml"


def load_config(path=None):
    """Return the configuration at `path` (default: configs/default.yaml) as a dict."""
    path = Path(path) if path is not None else DEFAULT_CONFIG
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

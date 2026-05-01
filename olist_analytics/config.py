"""Configuration handling.

Loads a YAML config file describing where the Olist CSVs live and what
analytical thresholds to apply. Defaults are bundled in `configs/default.yaml`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "default.yaml"


@dataclass
class Config:
    """Project configuration — paths and analytical thresholds."""

    data_dir: Path
    output_dir: Path
    thresholds: dict[str, Any] = field(default_factory=dict)
    state_population_m: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: str | Path | None = None) -> "Config":
        """Load a config from a YAML file. Falls back to the bundled default."""
        path = Path(path) if path else DEFAULT_CONFIG_PATH
        if not path.exists():
            raise FileNotFoundError(f"Config not found: {path}")

        with path.open("r") as f:
            raw = yaml.safe_load(f)

        return cls(
            data_dir=Path(raw["data_dir"]).expanduser(),
            output_dir=Path(raw.get("output_dir", "reports/figures")).expanduser(),
            thresholds=raw.get("thresholds", {}),
            state_population_m=raw.get("state_population_m", {}),
        )

    def threshold(self, key: str, default: Any = None) -> Any:
        """Get a threshold value by key, with optional default."""
        return self.thresholds.get(key, default)

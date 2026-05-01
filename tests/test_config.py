"""Tests for config loading."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from olist_analytics.config import Config, DEFAULT_CONFIG_PATH


def test_default_config_loads():
    config = Config.from_yaml(DEFAULT_CONFIG_PATH)
    assert config.data_dir is not None
    assert config.output_dir is not None
    # Sanity: the bundled default contains some thresholds and SP population
    assert "edge_month_min_orders" in config.thresholds
    assert config.state_population_m["SP"] > 0


def test_custom_config_loads(tmp_path: Path):
    custom = tmp_path / "custom.yaml"
    yaml.safe_dump(
        {
            "data_dir": "/tmp/data",
            "output_dir": "/tmp/out",
            "thresholds": {"edge_month_min_orders": 1000},
            "state_population_m": {"SP": 50.0},
        },
        custom.open("w"),
    )
    config = Config.from_yaml(custom)
    assert config.data_dir == Path("/tmp/data")
    assert config.threshold("edge_month_min_orders") == 1000
    assert config.state_population_m["SP"] == 50.0


def test_threshold_returns_default_for_missing_key():
    config = Config.from_yaml(DEFAULT_CONFIG_PATH)
    assert config.threshold("nonexistent_key", "fallback") == "fallback"


def test_missing_config_raises():
    with pytest.raises(FileNotFoundError):
        Config.from_yaml("/nonexistent/path/to/config.yaml")

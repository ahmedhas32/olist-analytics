"""Command-line interface — `olist-report` runs the full report.

Examples:
    olist-report                       # uses configs/default.yaml
    olist-report --config my.yaml      # custom config
    olist-report --data-dir ~/olist    # override the data path only
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from olist_analytics.config import Config, DEFAULT_CONFIG_PATH
from olist_analytics.report import run_all


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="olist-report",
        description="Run the Olist marketplace analytics report end-to-end.",
    )
    p.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the YAML config (default: configs/default.yaml).",
    )
    p.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Override the data directory from the config.",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override the output directory from the config.",
    )
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable INFO-level logging.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    config = Config.from_yaml(args.config)
    if args.data_dir is not None:
        config.data_dir = args.data_dir
    if args.output_dir is not None:
        config.output_dir = args.output_dir

    summary = run_all(config)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

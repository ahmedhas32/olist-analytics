# Olist Marketplace Analytics

> A decision-maker's view of the [Olist Brazilian e-commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — structured around the questions a platform CEO or COO would actually ask.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## What this is

Most analyses of the Olist dataset are technical exercises: clean code, lots of charts, but you finish reading and don't really know what a *platform operator* would do with any of it. This project takes the opposite angle.

The analysis is organized into **five sections**, each answering a question a leadership team would actually ask:

| Section | Question | Where to find it |
|---|---|---|
| 1. Marketplace overview | How big and how healthy is this marketplace? | `analyses/section1_overview.py` |
| 2. Geographic performance | Where are we strong, where are we under-developed? | `analyses/section2_geography.py` |
| 3. Seller performance & lifecycle | Is the supply side healthy? | `analyses/section3_sellers.py` |
| 4. Payment mix & non-completion | Where do orders fail, and what's the lever? | `analyses/section4_payments.py` |
| 5. Product categories & customer experience | What sells, and what hurts CX? | `analyses/section5_categories.py` |

Each section ends with an interpretation pointing to the decision the chart informs.

---

## Quickstart

### 1. Install

```bash
git clone https://github.com/ahmedhas32/olist-analytics.git
cd olist-analytics
pip install -e .
```

For development (pytest, ruff, jupyter):

```bash
pip install -e ".[dev]"
```

### 2. Get the data

Download the [Olist dataset from Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) (8 CSV files, ~45MB unzipped) and either:

- Place the CSVs in a directory and pass `--data-dir` to the CLI, or
- Edit `configs/default.yaml` to point `data_dir` at the directory.

### 3. Run the report

```bash
olist-report --data-dir /path/to/olist/csvs --output-dir reports/figures -v
```

Figures are written to `reports/figures/` as PNGs. Headline KPIs are printed to stdout as JSON.

### 4. Or use the notebook

```bash
jupyter notebook notebooks/report.ipynb
```

The notebook imports the same package functions, so the rendered output matches the CLI exactly. Charts appear inline; markdown explains each section's purpose and how to read it.

---

## Project structure

```
olist-analytics/
├── olist_analytics/              # The Python package
│   ├── __init__.py
│   ├── cli.py                    # `olist-report` entry point
│   ├── config.py                 # YAML config loader (paths, thresholds)
│   ├── style.py                  # matplotlib/seaborn theming + colors
│   ├── report.py                 # Top-level orchestrator (run_all)
│   ├── loaders/
│   │   └── olist.py              # Reads the 8 Olist CSVs
│   ├── transforms/
│   │   └── categories.py         # 70-categories → 7-groups taxonomy
│   └── analyses/
│       ├── section1_overview.py
│       ├── section2_geography.py
│       ├── section3_sellers.py
│       ├── section4_payments.py
│       └── section5_categories.py
├── configs/
│   └── default.yaml              # Paths, thresholds, IBGE state populations
├── notebooks/
│   └── report.ipynb              # Thin notebook that imports from the package
├── reports/figures/              # Generated PNG outputs
├── tests/
│   └── test_*.py                 # pytest unit tests
├── pyproject.toml                # Build, dependencies, CLI script, ruff config
├── requirements.txt              # Runtime dependencies (mirror of pyproject)
└── README.md
```

---

## Configuration

All paths and analytical thresholds live in `configs/default.yaml`. Override with `--config` at the CLI or programmatically:

```python
from olist_analytics.config import Config
from olist_analytics.report import run_all

config = Config.from_yaml("configs/default.yaml")
config.data_dir = Path("/my/local/olist")
summary = run_all(config)
```

Thresholds you'll most likely want to adjust:

| Key | Default | Used by |
|---|---|---|
| `edge_month_min_orders` | 500 | § 1.4 — months below this are excluded from the non-completion trend |
| `seller_min_orders_for_quality` | 10 | § 3.1 — sellers with fewer orders are excluded from quality panels |
| `cohort_min_sellers` | 30 | § 3.2 — minimum cohort size for the survival heatmap |
| `group_min_buyers` | 500 | § 5.2 — minimum buyers for a product group to appear on the repeat-rate chart |
| `merchant_churn_days` | 90 | § 1.1 — inactivity threshold for the churn KPI |

---

## Opinionated calls worth knowing about

A few methodological choices that go against typical exploratory-notebook habits — flagged here because they would otherwise look surprising:

- **GMV excludes freight and excludes non-delivered orders.** Freight is pass-through revenue to carriers; non-delivered orders are money that was never collected. Including either inflates the headline number.
- **Charts that don't change a decision were cut.** The order-status funnel was four nearly-equal bars — replaced with a one-line print. Cancellation rate by product group had a 0.28pp spread across all groups — replaced with a one-sentence null finding. A chart earns its place by showing meaningful separation.
- **Two denominators are honest, not a bug.** Platform-wide cancellation rate uses *all* orders. Cancellation rate by product group uses only orders with item records. They don't reconcile because canceled-no-items orders exist — and the gap is itself informative about how cancellations happen.
- **Cohort retention is presented as evidence, not as a KPI.** Olist's monthly retention is well under 1% even for the oldest cohorts. That's structural to a marketplace selling furniture, electronics, and beauty — the cohort heatmap is included to *prove* this is a transactional marketplace, not to be optimized.

---

## Development

```bash
# Run tests
pytest

# Lint + format
ruff check .
ruff format .

# Reinstall after local changes
pip install -e .
```

---

## Limitations

- **Observational data only.** No experimental treatment-vs-control split, no random assignment. The report identifies hypotheses worth testing but does not measure causal effects.
- **Dataset window is 2016-09 to 2018-10.** Edge months at both ends have very few orders and are excluded from time-series views.
- **Olist's category taxonomy is itself inconsistent** — the 7-group mapping in `transforms/categories.py` is hand-curated and includes known typos in the upstream slugs (`fashio_female_clothing`, `costruction_tools_garden`).

---

## License

MIT — see [LICENSE](LICENSE).

The Olist dataset itself is published by Olist on Kaggle under its own license; see the dataset page for terms.

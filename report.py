"""End-to-end report runner.

`run_all(config)` loads the data, runs every section, writes figures to
the configured output directory, and returns a summary dict so a caller
can print or log the headline numbers.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from olist_analytics.analyses import (
    section1_overview,
    section2_geography,
    section3_sellers,
    section4_payments,
    section5_categories,
)
from olist_analytics.config import Config
from olist_analytics.loaders import load_all
from olist_analytics.style import apply_style

logger = logging.getLogger(__name__)
wd = r'c:\Users\user\Downloads\repo'
os.chdir(wd)

def run_all(config: Config) -> dict[str, Any]:
    """Run every section. Save figures to `config.output_dir`. Return a summary."""
    apply_style()
    config = Config.from_yaml(wd+"/configs/default.yaml")
    data = load_all(config.data_dir)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {}

    # --- Section 1 ---
    logger.info("Section 1 — marketplace overview")
    summary["headline_kpis"] = section1_overview.compute_headline_kpis(data, config).as_dict()
    summary["funnel"] = section1_overview.order_lifecycle_funnel(data)
    _save(section1_overview.plot_marketplace_dashboard(data), config, "1_marketplace_dashboard")
    _save(section1_overview.plot_non_completion_trend(data, config), config, "1_non_completion_trend")

    # --- Section 2 ---
    logger.info("Section 2 — geography")
    state_table = section2_geography.build_state_table(data, config)
    _save(section2_geography.plot_penetration_vs_depth(state_table), config, "2_penetration_vs_depth")
    summary["state_table_top10"] = state_table.head(10).round(2).to_dict()

    # --- Section 3 ---
    logger.info("Section 3 — sellers")
    seller_stats = section3_sellers.build_seller_stats(data)
    _save(section3_sellers.plot_seller_dashboard(seller_stats, config), config, "3_seller_dashboard")
    survival = section3_sellers.build_seller_cohort_survival(data, config)
    _save(section3_sellers.plot_cohort_heatmap(survival), config, "3_cohort_survival")
    summary["seller_scale"] = section3_sellers.seller_scale_summary(data)

    # --- Section 4 ---
    logger.info("Section 4 — payments")
    _save(section4_payments.plot_payment_type_share(data), config, "4_payment_share")
    inst = section4_payments.installment_summary(data)
    _save(section4_payments.plot_installments(inst), config, "4_installments")
    pay_stats, stage_split, platform_avg = section4_payments.build_payment_completion_table(data, config)
    _save(
        section4_payments.plot_payment_completion(pay_stats, stage_split, platform_avg),
        config,
        "4_payment_completion",
    )
    summary["platform_incomplete_rate_pct"] = platform_avg

    # --- Section 5 ---
    logger.info("Section 5 — categories")
    rev = section5_categories.revenue_by_group(data)
    _save(section5_categories.plot_revenue_pie(rev), config, "5_revenue_share")
    repeat_table, overall_rate = section5_categories.same_category_repeat_table(data, config)
    _save(section5_categories.plot_repeat_rate(repeat_table, overall_rate), config, "5_repeat_rate")
    topics = section5_categories.negative_review_topics(data)
    _save(section5_categories.plot_negative_review_topics(topics), config, "5_negative_review_topics")
    summary["same_category_repeat_rate_pct"] = overall_rate

    logger.info("Done. Figures written to %s", config.output_dir)
    return summary


def _save(fig: "plt.Figure", config: Config, name: str) -> Path:
    """Save a matplotlib figure to `config.output_dir/<name>.png` and close it."""
    path = config.output_dir / f"{name}.png"
    print(f"Saving plot to: {path.absolute()}")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path
if __name__ == "__main__":
    from olist_analytics.config import Config
    # تأكد من تمرير الإعدادات الصحيحة هنا
    # cfg = Config(data_dir=Path("data"), output_dir=Path("output")) 
    results = run_all(Config)
    print("Summary:", results)
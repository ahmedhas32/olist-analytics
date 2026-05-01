"""Section 1 — marketplace overview.

Headline KPIs, the four-panel marketplace dashboard, and the non-completion
trend over time.
"""
from __future__ import annotations

from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from olist_analytics.config import Config
from olist_analytics.loaders import OlistData
from olist_analytics.style import PX_BLUE, PX_GREEN, PX_PURPLE, PX_RED, PX_YELLOW


@dataclass
class HeadlineKPIs:
    """The five headline numbers that anchor the report."""

    gmv: float
    aov: float
    repeat_rate_pct: float
    merchant_churn_pct: float
    negative_review_pct: float

    def as_dict(self) -> dict[str, float]:
        return {
            "gmv": self.gmv,
            "aov": self.aov,
            "repeat_rate_pct": self.repeat_rate_pct,
            "merchant_churn_pct": self.merchant_churn_pct,
            "negative_review_pct": self.negative_review_pct,
        }


def compute_headline_kpis(data: OlistData, config: Config) -> HeadlineKPIs:
    """Compute the headline KPIs reported in section 1.1.

    Notes on definitions:
        - GMV excludes freight (freight is pass-through to carriers).
        - Merchant churn uses the inactivity threshold from `config`.
    """
    items = data.order_items
    gmv = float(items["price"].sum())

    aov = float(data.order_payments.groupby("order_id")["payment_value"].sum().mean())

    cust_orders = data.orders.merge(data.customers, on="customer_id")
    repeat_rate = (
        cust_orders.groupby("customer_unique_id")["order_id"].nunique() > 1
    ).mean() * 100

    merchant_churn = _merchant_churn_rate(
        data, threshold_days=config.threshold("merchant_churn_days", 90)
    )

    neg_review_pct = (data.order_reviews["review_score"] <= 2).mean() * 100

    return HeadlineKPIs(
        gmv=gmv,
        aov=aov,
        repeat_rate_pct=float(repeat_rate),
        merchant_churn_pct=float(merchant_churn),
        negative_review_pct=float(neg_review_pct),
    )


def _merchant_churn_rate(data: OlistData, threshold_days: int) -> float:
    """% of sellers whose last sale was more than `threshold_days` ago."""
    last_sale = (
        data.order_items.merge(
            data.orders[["order_id", "order_purchase_timestamp"]], on="order_id"
        )
        .groupby("seller_id")["order_purchase_timestamp"]
        .max()
    )
    max_date = data.orders["order_purchase_timestamp"].max()
    days_since_last = (max_date - last_sale).dt.days
    return float((days_since_last > threshold_days).mean() * 100)


def plot_marketplace_dashboard(data: OlistData) -> plt.Figure:
    """Render the four-panel marketplace dashboard (GMV, sellers, reviews, loyalty)."""
    items = data.order_items
    orders = data.orders
    reviews = data.order_reviews
    customers = data.customers

    df_merged = items.merge(orders[["order_id", "order_purchase_timestamp"]], on="order_id")
    df_merged["month_yr"] = df_merged["order_purchase_timestamp"].dt.to_period("M").astype(str)

    monthly_gmv = df_merged.groupby("month_yr")["price"].sum()
    active_sellers = df_merged.groupby("month_yr")["seller_id"].nunique()
    review_counts = reviews["review_score"].value_counts().sort_index()

    cust_orders = orders.merge(customers, on="customer_id")
    order_counts = cust_orders.groupby("customer_unique_id")["order_id"].nunique()
    repeat_n = int((order_counts > 1).sum())
    one_time_n = int((order_counts == 1).sum())

    neg_review_pct = (reviews["review_score"] <= 2).mean() * 100

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle("Marketplace Performance: Loyalty Focus", fontsize=16, fontweight="bold", y=1.00)

    # Panel 1 — Monthly GMV
    ax = axes[0, 0]
    x = range(len(monthly_gmv))
    ax.fill_between(x, monthly_gmv.values, color=PX_BLUE, alpha=0.35)
    ax.plot(x, monthly_gmv.values, color=PX_BLUE, linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels(monthly_gmv.index, rotation=45, ha="right", fontsize=8)
    ax.set_title("1. Monthly GMV")
    ax.set_ylabel("GMV (R$)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1e6:.1f}M"))

    # Panel 2 — Active sellers
    ax = axes[0, 1]
    ax.bar(range(len(active_sellers)), active_sellers.values, color=PX_BLUE)
    ax.set_xticks(range(len(active_sellers)))
    ax.set_xticklabels(active_sellers.index, rotation=45, ha="right", fontsize=8)
    ax.set_title("2. Active Merchant Growth")
    ax.set_ylabel("# of active sellers")

    # Panel 3 — Review distribution
    ax = axes[1, 0]
    colors = [PX_RED, PX_YELLOW, PX_GREEN, PX_GREEN, PX_GREEN]
    bars = ax.bar(review_counts.index.astype(str), review_counts.values, color=colors)
    ax.set_title(f"3. Review Distribution (Negatives: {neg_review_pct:.2f}%)")
    ax.set_xlabel("Review score")
    ax.set_ylabel("# of reviews")
    for b, v in zip(bars, review_counts.values):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,}", ha="center", va="bottom", fontsize=8)

    # Panel 4 — Loyalty donut
    ax = axes[1, 1]
    ax.pie(
        [repeat_n, one_time_n],
        labels=["Repeat", "One-time"],
        colors=[PX_PURPLE, PX_BLUE],
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=dict(width=0.4, edgecolor="white"),
        textprops=dict(fontsize=10),
    )
    ax.set_title("4. Customer Loyalty")

    fig.tight_layout()
    return fig


def order_lifecycle_funnel(data: OlistData) -> dict[str, tuple[int, float]]:
    """Compute order lifecycle counts: placed → approved → shipped → delivered.

    Returns a dict mapping stage name to `(count, pct_of_placed)`.
    """
    orders = data.orders
    total = len(orders)
    stages = {
        "Placed": total,
        "Approved": int(orders["order_approved_at"].notna().sum()),
        "Shipped": int(orders["order_delivered_carrier_date"].notna().sum()),
        "Delivered": int(orders["order_delivered_customer_date"].notna().sum()),
    }
    return {k: (v, v / total * 100) for k, v in stages.items()}


def plot_non_completion_trend(data: OlistData, config: Config) -> plt.Figure:
    """Plot % of incomplete orders by month, trimming low-volume edge months."""
    incomplete_statuses = config.threshold("incomplete_order_statuses", ["canceled", "unavailable"])
    min_orders = int(config.threshold("edge_month_min_orders", 500))

    orders = data.orders.copy()
    orders["month_yr"] = orders["order_purchase_timestamp"].dt.to_period("M").astype(str)
    monthly = (
        orders.groupby("month_yr")["order_status"]
        .agg(total="count", incomplete=lambda s: s.isin(incomplete_statuses).sum())
        .sort_index()
    )
    monthly["incomplete_pct"] = monthly["incomplete"] / monthly["total"] * 100
    trimmed = monthly[monthly["total"] >= min_orders]

    fig, ax = plt.subplots(figsize=(11, 4))
    ax.fill_between(trimmed.index, trimmed["incomplete_pct"], color=PX_RED, alpha=0.15)
    ax.plot(trimmed.index, trimmed["incomplete_pct"], marker="o", color=PX_RED, linewidth=2)

    median = trimmed["incomplete_pct"].median()
    ax.axhline(median, color="gray", linestyle="--", linewidth=1, label=f"Median {median:.1f}%")

    ax.set_title(f"Non-completed orders by month (months with ≥{min_orders} orders)")
    ax.set_ylabel("% of orders")
    ax.set_ylim(0, max(5, trimmed["incomplete_pct"].max() * 1.4))
    ax.legend(loc="upper left")
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    fig.tight_layout()
    return fig

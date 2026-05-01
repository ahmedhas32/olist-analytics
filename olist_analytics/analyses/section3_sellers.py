"""Section 3 — seller performance & lifecycle.

Seller quality distribution, quality-vs-volume scatter, Pareto concentration,
and quarterly-cohort survival heatmap.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from olist_analytics.config import Config
from olist_analytics.loaders import OlistData
from olist_analytics.style import PX_BLUE, PX_GRAY, PX_GREEN, PX_PURPLE, PX_RED


def build_seller_stats(data: OlistData) -> pd.DataFrame:
    """Per-seller aggregates: avg review, total sales, order count.

    Joins items → reviews. Keeps every seller; downstream code filters by
    minimum order count when computing quality-sensitive views.
    """
    seller_reviews = data.order_items.merge(
        data.order_reviews[["order_id", "review_score"]], on="order_id"
    )
    return (
        seller_reviews.groupby("seller_id")
        .agg(
            avg_review=("review_score", "mean"),
            total_sales=("price", "sum"),
            order_count=("order_id", "count"),
        )
    )


def plot_seller_dashboard(seller_stats: pd.DataFrame, config: Config) -> plt.Figure:
    """Four-panel seller dashboard:
        1. Quality distribution (histogram)
        2. Quality-vs-volume (log scatter, color = avg review)
        3. Pareto curve (cumulative GMV share)
        4. Top-10 vs the rest (donut)
    """
    min_orders = int(config.threshold("seller_min_orders_for_quality", 10))
    quality_subset = seller_stats[seller_stats["order_count"] >= min_orders]

    sorted_sales = seller_stats["total_sales"].sort_values(ascending=False).values
    cum_share = np.cumsum(sorted_sales) / sorted_sales.sum() * 100
    x_pct = np.arange(1, len(sorted_sales) + 1) / len(sorted_sales) * 100

    fig, axes = plt.subplots(2, 2, figsize=(15, 11))
    fig.suptitle("Seller Performance & Quality Intelligence", fontsize=16, fontweight="bold", y=1.00)

    # 1 — quality distribution
    ax = axes[0, 0]
    ax.hist(quality_subset["avg_review"], bins=20, color=PX_GREEN, alpha=0.85, edgecolor="white")
    mean_val = quality_subset["avg_review"].mean()
    ax.axvline(mean_val, color="#2c3e50", linestyle="--", linewidth=1.5)
    ax.text(
        mean_val, ax.get_ylim()[1] * 0.95, f" mean {mean_val:.2f}",
        fontsize=9, color="#2c3e50", va="top",
    )
    ax.set_title("Seller quality distribution (avg review per seller)")
    ax.set_xlabel("Avg review score")
    ax.set_ylabel("# of sellers")

    # 2 — quality vs volume
    ax = axes[0, 1]
    sizes = np.clip(quality_subset["order_count"] ** 0.5, 4, 25) * 3
    sc = ax.scatter(
        quality_subset["total_sales"],
        quality_subset["avg_review"],
        s=sizes,
        c=quality_subset["avg_review"],
        cmap="RdYlGn",
        vmin=1, vmax=5,
        alpha=0.55,
        edgecolor="none",
    )
    ax.set_xscale("log")
    ax.axhline(mean_val, color=PX_RED, linestyle=":", linewidth=1.5)
    ax.text(
        ax.get_xlim()[1], mean_val, f" quality floor {mean_val:.2f}",
        color=PX_RED, fontsize=8, va="bottom", ha="right",
    )
    ax.set_title(f"Quality vs volume (sellers with ≥{min_orders} orders)")
    ax.set_xlabel("Total sales (R$, log scale)")
    ax.set_ylabel("Avg review score")
    ax.set_ylim(0.8, 5.2)
    plt.colorbar(sc, ax=ax, label="Avg review")

    # 3 — Pareto
    ax = axes[1, 0]
    ax.plot(x_pct, cum_share, color=PX_PURPLE, linewidth=2.5)
    ax.axvline(20, color="gray", linestyle="--")
    at_20 = cum_share[int(len(cum_share) * 0.2) - 1] if len(cum_share) else 0
    ax.annotate(
        f"Top 20% → {at_20:.1f}% of revenue",
        xy=(20, at_20), xytext=(30, at_20 - 15),
        fontsize=9, color="#444",
        arrowprops=dict(arrowstyle="->", color="gray"),
    )
    ax.set_title("Seller concentration — cumulative revenue share")
    ax.set_xlabel("% of sellers (sorted by revenue)")
    ax.set_ylabel("Cumulative revenue %")
    ax.set_ylim(0, 105)

    # 4 — top-10 vs rest
    ax = axes[1, 1]
    top10_sum = float(seller_stats.nlargest(10, "total_sales")["total_sales"].sum())
    other_sum = float(seller_stats["total_sales"].sum() - top10_sum)
    ax.pie(
        [top10_sum, other_sum],
        labels=["Top 10 sellers", "All other sellers"],
        autopct="%1.1f%%",
        startangle=90,
        colors=[PX_BLUE, PX_GRAY],
        wedgeprops=dict(width=0.4, edgecolor="white"),
        textprops=dict(fontsize=10),
    )
    ax.set_title("Top 10 vs. the rest")

    fig.tight_layout()
    return fig


def build_seller_cohort_survival(data: OlistData, config: Config) -> pd.DataFrame:
    """Quarterly seller-cohort survival table (% still active in Q+n).

    Returns a DataFrame indexed by cohort (PeriodIndex, freq=Q) with one
    column per offset Q+1, Q+2, ... Cells beyond the data window are NaN.
    """
    min_cohort = int(config.threshold("cohort_min_sellers", 30))

    seller_sales = data.order_items.merge(
        data.orders[["order_id", "order_purchase_timestamp", "order_status"]],
        on="order_id",
    )
    seller_sales = seller_sales[seller_sales["order_status"] == "delivered"].copy()
    seller_sales["active_q"] = seller_sales["order_purchase_timestamp"].dt.to_period("Q")

    first_q = seller_sales.groupby("seller_id")["active_q"].min().rename("cohort_q")
    seller_sales = seller_sales.merge(first_q, on="seller_id")
    seller_sales["quarters_since"] = (
        seller_sales["active_q"] - seller_sales["cohort_q"]
    ).apply(lambda p: p.n)

    survival = (
        seller_sales[["seller_id", "cohort_q", "quarters_since"]]
        .drop_duplicates()
        .groupby(["cohort_q", "quarters_since"])["seller_id"]
        .nunique()
        .unstack(fill_value=0)
        .sort_index(axis=1)
    )
    survival_pct = survival.div(survival.iloc[:, 0], axis=0) * 100
    survival_pct = survival_pct.loc[survival.iloc[:, 0] >= min_cohort]
    survival_pct = survival_pct.iloc[:, 1:]  # drop Q+0 (always 100%)

    # Mask un-observable cells: if a cohort hasn't existed for Q+n yet, blank it
    data_max_q = pd.Period(data.orders["order_purchase_timestamp"].max(), "Q")
    out = survival_pct.copy().astype(float)
    for cohort in out.index:
        horizon = (data_max_q - cohort).n
        for q in out.columns:
            if int(q) > horizon:
                out.loc[cohort, q] = np.nan
    return out


def plot_cohort_heatmap(survival_pct: pd.DataFrame) -> plt.Figure:
    """Heatmap of seller-cohort survival.

    Color scale capped at 40% so the meaningful retention range gets the full
    palette (the trivial 100% Q+0 column has been dropped upstream).
    """
    display = survival_pct.copy()
    display.index = display.index.to_series().apply(lambda p: p.strftime("Q%q-%y"))

    fig, ax = plt.subplots(figsize=(14, 9))
    im = ax.imshow(display.values, cmap="Purples", aspect="auto", vmin=0, vmax=40)
    ax.set_xticks(range(len(display.columns)))
    ax.set_xticklabels([f"Q+{c}" for c in display.columns])
    ax.set_yticks(range(len(display.index)))
    ax.set_yticklabels([str(c) for c in display.index])
    ax.set_xlabel("Quarters since first delivered sale")
    ax.set_ylabel("Acquisition cohort")
    ax.set_title("Seller-cohort survival (% still active in Q+n)")

    for i in range(display.shape[0]):
        for j in range(display.shape[1]):
            v = display.values[i, j]
            if not np.isnan(v):
                ax.text(
                    j, i, f"{v:.0f}", ha="center", va="center",
                    fontsize=11, color="white" if v > 20 else "black",
                )

    plt.colorbar(im, ax=ax, fraction=0.04).set_label("% active")
    fig.tight_layout()
    return fig


def seller_scale_summary(data: OlistData) -> dict[str, int]:
    """Two scale numbers to print alongside the cohort heatmap.

    The heatmap shows percentages, not absolute counts — these provide context.
    """
    seller_sales = data.order_items.merge(
        data.orders[["order_id", "order_purchase_timestamp", "order_status"]],
        on="order_id",
    )
    seller_sales = seller_sales[seller_sales["order_status"] == "delivered"]
    total_sellers = int(seller_sales["seller_id"].nunique())

    cutoff = seller_sales["order_purchase_timestamp"].max() - pd.Timedelta(days=30)
    final_30d = int(
        seller_sales[seller_sales["order_purchase_timestamp"] >= cutoff]["seller_id"].nunique()
    )
    return {"total_sellers": total_sellers, "active_final_30d": final_30d}

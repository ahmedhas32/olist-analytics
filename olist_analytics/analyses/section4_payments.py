"""Section 4 — payment mix & non-completion drivers.

Payment-type share of GMV, credit-card installment buckets, and the
non-completion-by-payment-type breakdown that splits cancellations into
pre-approval and post-approval lifecycle stages.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from olist_analytics.config import Config
from olist_analytics.loaders import OlistData
from olist_analytics.style import PX_BLUE, PX_GREEN, PX_RED, PX_YELLOW


# ---------------------------------------------------------------------------
# 4.1 — payment-type share of GMV
# ---------------------------------------------------------------------------

def plot_payment_type_share(data: OlistData) -> plt.Figure:
    """Donut: share of total GMV by payment type."""
    type_mix = (
        data.order_payments.groupby("payment_type")["payment_value"]
        .sum()
        .sort_values(ascending=False)
    )

    palette = sns.color_palette("Set2", n_colors=len(type_mix))
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.pie(
        type_mix.values,
        labels=type_mix.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=palette,
        wedgeprops=dict(width=0.5, edgecolor="white"),
        textprops=dict(fontsize=10),
    )
    ax.set_title("Payment type — share of GMV")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 4.2 — credit-card installment buckets
# ---------------------------------------------------------------------------

INSTALLMENT_BUCKETS = ["1× (single)", "2–3× (short)", "4–9× (long)", "10×+ (very long)"]


def _bucket_installment(n: int) -> str:
    if n == 1:
        return "1× (single)"
    if n <= 3:
        return "2–3× (short)"
    if n <= 9:
        return "4–9× (long)"
    return "10×+ (very long)"


def installment_summary(data: OlistData) -> pd.DataFrame:
    """Aggregates credit-card payments by installment bucket.

    Columns: orders, gmv, orders_pct, gmv_pct, avg_ticket.
    Index: ordered list of bucket labels.
    """
    cc = data.order_payments[data.order_payments["payment_type"] == "credit_card"].copy()
    cc["bucket"] = cc["payment_installments"].apply(_bucket_installment)

    agg = (
        cc.groupby("bucket")
        .agg(
            orders=("order_id", "nunique"),
            gmv=("payment_value", "sum"),
            avg_ticket=("payment_value", "mean"),
        )
        .reindex(INSTALLMENT_BUCKETS)
    )
    agg["orders_pct"] = agg["orders"] / agg["orders"].sum() * 100
    agg["gmv_pct"] = agg["gmv"] / agg["gmv"].sum() * 100
    return agg


def plot_installments(installment_table: pd.DataFrame) -> plt.Figure:
    """Two side-by-side bars: % of CC orders vs % of CC GMV per bucket."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    fig.suptitle(
        "Credit-card installments — share of orders vs share of GMV",
        fontsize=13, fontweight="bold",
    )

    for ax, col, color, title in [
        (axes[0], "orders_pct", PX_BLUE, "% of credit-card orders"),
        (axes[1], "gmv_pct", PX_GREEN, "% of credit-card GMV"),
    ]:
        bars = ax.bar(installment_table.index, installment_table[col], color=color)
        for b, v in zip(bars, installment_table[col]):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}%", ha="center", va="bottom", fontsize=9)
        ax.set_title(title)
        ax.set_ylabel(title.split(" of ")[-1])
        ax.set_ylim(0, installment_table[col].max() * 1.18)
        plt.setp(ax.get_xticklabels(), rotation=15, ha="right", fontsize=9)

    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 4.3 — non-completion by payment type
# ---------------------------------------------------------------------------

def build_payment_completion_table(
    data: OlistData, config: Config
) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Build tables behind the payment-type non-completion chart.

    Returns:
        - pay_stats: orders, incomplete count, rate per payment type.
        - stage_split_pct: pre-approval vs post-approval cancel %, per type.
        - platform_avg: weighted incomplete rate across all valid orders.
    """
    incomplete_statuses = config.threshold("incomplete_order_statuses", ["canceled", "unavailable"])

    primary = (
        data.order_payments.sort_values("payment_value", ascending=False)
        .drop_duplicates("order_id")[["order_id", "payment_type"]]
    )

    orders_pay = data.orders.merge(primary, on="order_id", how="left")
    orders_pay["is_incomplete"] = orders_pay["order_status"].isin(incomplete_statuses)
    orders_pay = orders_pay[
        orders_pay["payment_type"].notna() & (orders_pay["payment_type"] != "not_defined")
    ]

    pay_stats = (
        orders_pay.groupby("payment_type")
        .agg(orders=("order_id", "nunique"), incomplete=("is_incomplete", "sum"))
        .assign(rate=lambda d: d["incomplete"] / d["orders"] * 100)
        .sort_values("rate")
    )

    canceled = orders_pay[orders_pay["order_status"] == "canceled"].copy()
    canceled["stage"] = np.where(
        canceled["order_approved_at"].isna(), "pre_approval", "post_approval"
    )
    stage_split = (
        canceled.groupby(["payment_type", "stage"]).size()
        .unstack(fill_value=0)
        .reindex(pay_stats.index)
    )
    stage_split_pct = stage_split.div(pay_stats["orders"], axis=0) * 100

    platform_avg = float(orders_pay["is_incomplete"].mean() * 100)
    return pay_stats, stage_split_pct, platform_avg


def plot_payment_completion(
    pay_stats: pd.DataFrame, stage_split_pct: pd.DataFrame, platform_avg: float
) -> plt.Figure:
    """Two-panel chart: total incomplete rate + pre/post approval split per payment type."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))

    ax = axes[0]
    bars = ax.barh(pay_stats.index, pay_stats["rate"], color=PX_RED)
    ax.axvline(platform_avg, color="gray", linestyle="--", linewidth=1, label=f"Platform avg ({platform_avg:.2f}%)")
    for b, v, n in zip(bars, pay_stats["rate"], pay_stats["orders"]):
        ax.text(
            v, b.get_y() + b.get_height() / 2,
            f"  {v:.2f}%  (n={int(n):,})",
            va="center", fontsize=8,
        )
    ax.set_xlabel("Incomplete orders (%)")
    ax.set_title("Non-completion rate by primary payment type")
    ax.legend(loc="lower right")

    ax = axes[1]
    pre = stage_split_pct.get("pre_approval", pd.Series(0, index=stage_split_pct.index))
    post = stage_split_pct.get("post_approval", pd.Series(0, index=stage_split_pct.index))
    ax.barh(stage_split_pct.index, pre, color=PX_YELLOW, label="Canceled before approval")
    ax.barh(stage_split_pct.index, post, left=pre, color=PX_RED, label="Canceled after approval")
    ax.set_xlabel("% of payment-type orders")
    ax.set_title("Where in the lifecycle do cancellations happen?")
    ax.legend(loc="lower right", fontsize=8)

    fig.tight_layout()
    return fig

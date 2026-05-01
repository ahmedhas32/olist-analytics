"""Section 5 — product categories & customer experience.

Revenue share by group (delivered orders, item value only); same-category
repeat-rate ranking; and keyword-based topic extraction over Portuguese
negative-review text.
"""
from __future__ import annotations

import re

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import seaborn as sns

from olist_analytics.config import Config
from olist_analytics.loaders import OlistData
from olist_analytics.style import PX_GREEN, PX_RED
from olist_analytics.transforms import assign_groups


# ---------------------------------------------------------------------------
# 5.1 — revenue share by group
# ---------------------------------------------------------------------------

def revenue_by_group(data: OlistData) -> pd.Series:
    """Revenue per product group, delivered orders only, item value only.

    Note: deliberately excludes freight (pass-through revenue) and non-delivered
    orders (cancellations should not count toward platform revenue).
    """
    if 'product_category_name' not in data.order_items.columns:
        data.order_items = data.order_items.merge(
        data.products, on='product_id', how='left'
    )
    items_with_groups = assign_groups(data.order_items, data.category_translation)
    df = items_with_groups.merge(
        data.orders[["order_id", "order_status"]], on="order_id"
    )
    df = df[df["order_status"] == "delivered"]
    return df.groupby("group")["price"].sum().sort_values(ascending=False)


def plot_revenue_pie(revenue_series: pd.Series) -> plt.Figure:
    """Donut chart of revenue share by group."""
    fig, ax = plt.subplots(figsize=(10, 7))
    palette = sns.color_palette("Set2", n_colors=len(revenue_series))
    _, _, autotexts = ax.pie(
        revenue_series.values,
        labels=revenue_series.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=palette,
        pctdistance=0.78,
        wedgeprops=dict(width=0.4, edgecolor="white"),
        textprops=dict(fontsize=10),
    )
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title("Revenue share by product group", fontsize=14, fontweight="bold", pad=15)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 5.2 — same-category repeat rate
# ---------------------------------------------------------------------------

def same_category_repeat_table(data: OlistData, config: Config) -> tuple[pd.DataFrame, float]:
    """Per-group same-category repeat rate.

    Returns:
        - DataFrame indexed by group, with columns: buyers, repeat_buyers, repeat_rate
        - Platform-wide same-category repeat rate as a single float (%)
    """
    min_buyers = int(config.threshold("group_min_buyers", 500))

    items_with_groups = assign_groups(data.order_items, data.category_translation)
    cust_cat = (
        items_with_groups[["order_id", "group"]]
        .merge(
            data.orders[["order_id", "customer_id", "order_status"]], on="order_id"
        )
        .merge(
            data.customers[["customer_id", "customer_unique_id"]], on="customer_id"
        )
    )
    cust_cat = cust_cat[cust_cat["order_status"] == "delivered"]

    cust_grp_orders = (
        cust_cat.groupby(["customer_unique_id", "group"])["order_id"]
        .nunique()
        .reset_index(name="orders_in_cat")
    )
    cust_grp_orders["repeat_same"] = cust_grp_orders["orders_in_cat"] > 1

    cat_stats = (
        cust_grp_orders.groupby("group")
        .agg(
            buyers=("customer_unique_id", "nunique"),
            repeat_buyers=("repeat_same", "sum"),
        )
        .assign(repeat_rate=lambda d: d["repeat_buyers"] / d["buyers"] * 100)
    )
    cat_filtered = cat_stats[cat_stats["buyers"] >= min_buyers]
    overall = float(cat_stats["repeat_buyers"].sum() / cat_stats["buyers"].sum() * 100)
    return cat_filtered, overall


def plot_repeat_rate(cat_table: pd.DataFrame, overall_rate: float, top_n: int = 10) -> plt.Figure:
    """Horizontal bar of same-category repeat rate, with platform-avg reference."""
    top_rate = cat_table.nlargest(top_n, "repeat_rate").sort_values("repeat_rate")

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(top_rate.index, top_rate["repeat_rate"], color=PX_GREEN)
    ax.set_title(f"Top {top_n} by same-category repeat rate (platform avg: {overall_rate:.2f}%)")
    ax.set_xlabel("% of buyers who purchased in the same group again")
    ax.axvline(overall_rate, color="gray", linestyle="--", linewidth=1, label=f"Platform avg ({overall_rate:.2f}%)")
    for b, v in zip(bars, top_rate["repeat_rate"]):
        ax.text(v, b.get_y() + b.get_height() / 2, f" {v:.2f}%", va="center", fontsize=9)
    ax.legend(loc="lower right")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# 5.3 — drivers of negative reviews (Portuguese keyword extraction)
# ---------------------------------------------------------------------------

# Topic name → (Portuguese regex, English label).
# Patterns are intentionally permissive; one review can match multiple topics.
NEGATIVE_REVIEW_TOPICS = {
    "Não recebeu / Nunca chegou": (
        r"nao? (receb|chegou?|entreg|chegar|receber)",
        "Didn't receive / Never arrived",
    ),
    "Atraso na entrega / Demora": (
        r"(atras|demor|praz[ao]|demorou|atrasou|esper)",
        "Delivery delay",
    ),
    "Produto errado ou trocado": (
        r"(errad|diferent|trocad|veio outro|veio errad|produto diferente)",
        "Wrong or swapped product",
    ),
    "Veio quebrado / com defeito": (
        r"(quebrad|defeit|danif|avariad|estragad|quebrou|danificado)",
        "Broken / Defective product",
    ),
    "Faltando peça / Incompleto": (
        r"(falt|faltando|faltou|incomplet|menos|faltante)",
        "Missing parts / Incomplete",
    ),
    "Problemas com reembolso": (
        r"(reembols|estorn|devolu|dinheiro de volta|solicito reembolso)",
        "Refund issues",
    ),
    "Atendimento ruim / Sem resposta": (
        r"(atend|suporte|liguei|sac|resposta|ignor|atendimento|não responder)",
        "Poor customer service",
    ),
    "Qualidade ruim do produto": (
        r"(qualidad|ruim|péssim|frágil|não funciona|não serve)",
        "Poor product quality",
    ),
}


def negative_review_topics(data: OlistData) -> pd.DataFrame:
    """% of 1–2★ reviews mentioning each topic.

    Returns a DataFrame sorted by Pct ascending (so it plots cleanly with
    `barh`). Columns: Topic_PT, Topic_EN, Count, Pct.
    """
    neg = data.order_reviews[data.order_reviews["review_score"] <= 2].copy()
    total_neg = len(neg)
    msgs = neg["review_comment_message"].fillna("").str.lower()

    rows = []
    for topic_pt, (pattern, topic_en) in NEGATIVE_REVIEW_TOPICS.items():
        matches = msgs.str.contains(pattern, regex=True, na=False)
        count = int(matches.sum())
        pct = round((count / total_neg * 100) if total_neg else 0, 1)
        rows.append({"Topic_PT": topic_pt, "Topic_EN": topic_en, "Count": count, "Pct": pct})

    return pd.DataFrame(rows).sort_values("Pct")


def plot_negative_review_topics(topic_df: pd.DataFrame) -> plt.Figure:
    """Horizontal bar of topic prevalence among negative reviews."""
    fig, ax = plt.subplots(figsize=(12, 7))
    bars = ax.barh(topic_df["Topic_EN"], topic_df["Pct"], color=PX_RED)
    for b, pct, cnt in zip(bars, topic_df["Pct"], topic_df["Count"]):
        ax.text(pct, b.get_y() + b.get_height() / 2, f" {pct}%  (n={cnt:,})", va="center", fontsize=9)

    ax.set_title(
        "Main Drivers of Negative Reviews (Score 1–2★)\n"
        "Percentage of unhappy customers who mentioned each topic",
        fontsize=13, fontweight="bold", loc="left",
    )
    ax.set_xlabel("% of Negative Reviews")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))
    ax.set_xlim(0, topic_df["Pct"].max() * 1.2)
    fig.tight_layout()
    return fig

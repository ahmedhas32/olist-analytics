"""Section 2 — geographic performance.

Per-state KPIs (GMV, buyers, sellers, freight) plus the penetration-vs-depth
quadrant scatter that anchors the geographic strategy view.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from olist_analytics.config import Config
from olist_analytics.loaders import OlistData
from olist_analytics.style import PX_BLUE


def build_state_table(data: OlistData, config: Config) -> pd.DataFrame:
    """Per-state KPIs: GMV, buyers, sellers, freight ratio, per-capita metrics.

    Index is state code (e.g. SP, RJ). Columns include:
        gmv, freight, orders, buyers, freight_pct_of_price, gmv_per_buyer,
        sellers, population_m, gmv_per_capita, buyers_per_1k, sellers_per_1k.
    """
    geo = (
        data.orders.merge(
            data.customers[["customer_id", "customer_state"]], on="customer_id"
        )
        .merge(
            data.order_items[["order_id", "price", "freight_value", "seller_id"]],
            on="order_id",
        )
    )

    state = (
        geo.groupby("customer_state")
        .agg(
            gmv=("price", "sum"),
            freight=("freight_value", "sum"),
            orders=("order_id", "nunique"),
            buyers=("customer_id", "nunique"),
        )
        .sort_values("gmv", ascending=False)
    )
    state["freight_pct_of_price"] = state["freight"] / state["gmv"] * 100
    state["gmv_per_buyer"] = state["gmv"] / state["buyers"]

    state_sellers = data.sellers.groupby("seller_state").size().rename("sellers").to_frame()
    state = state.join(state_sellers, how="left").fillna({"sellers": 0})

    state["population_m"] = state.index.map(config.state_population_m)
    state["gmv_per_capita"] = state["gmv"] / state["population_m"]
    state["buyers_per_1k"] = state["buyers"] / (state["population_m"] * 1e3)
    state["sellers_per_1k"] = state["sellers"] / (state["population_m"] * 1e3)
    return state


def plot_penetration_vs_depth(state_table: pd.DataFrame, top_n: int = 20) -> plt.Figure:
    """Quadrant scatter: GMV-per-capita (x) vs GMV-per-buyer (y), sized by buyers.

    Each quadrant maps to a distinct strategic posture:
        - Top-right (strong on both)         → defend, cross-sell
        - Top-left (high depth, low penetr.) → acquisition opportunity
        - Bottom-right                       → AOV / basket-size lever
        - Bottom-left                        → under-developed market
    """
    plot_data = state_table.head(top_n).copy()
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(
        plot_data["gmv_per_capita"],
        plot_data["gmv_per_buyer"],
        s=plot_data["buyers"] / 50,
        alpha=0.6,
        color=PX_BLUE,
        edgecolor="white",
        linewidth=1,
    )
    for state, row in plot_data.iterrows():
        ax.annotate(
            state,
            (row["gmv_per_capita"], row["gmv_per_buyer"]),
            fontsize=9,
            ha="center",
            va="center",
        )

    ax.axvline(plot_data["gmv_per_capita"].median(), color="gray", linestyle="--", linewidth=1)
    ax.axhline(plot_data["gmv_per_buyer"].median(), color="gray", linestyle="--", linewidth=1)
    ax.set_xlabel("Penetration: GMV per capita (R$)")
    ax.set_ylabel("Depth: GMV per buyer (R$)")
    ax.set_title("Geographic positioning — penetration vs. depth")

    for x, y, ha, va, txt in [
        (0.97, 0.97, "right", "top", "Strong on both"),
        (0.03, 0.97, "left", "top", "Few but valuable customers"),
        (0.97, 0.03, "right", "bottom", "Many but low-spend customers"),
        (0.03, 0.03, "left", "bottom", "Under-developed market"),
    ]:
        ax.text(x, y, txt, transform=ax.transAxes, ha=ha, va=va, fontsize=8, alpha=0.6)

    fig.tight_layout()
    return fig

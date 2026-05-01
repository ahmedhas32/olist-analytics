"""Plot styling — colors and matplotlib rcParams.

Colors mirror Plotly's default palette so charts in this project look
consistent with the original Plotly-based exploration notebooks.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import seaborn as sns

# Plotly-equivalent palette
PX_BLUE = "#636EFA"
PX_RED = "#EF553B"
PX_GREEN = "#00CC96"
PX_PURPLE = "#AB63FA"
PX_ORANGE = "#FFA15A"
PX_YELLOW = "#FECB52"
PX_GRAY = "#d3d3d3"


def apply_style() -> None:
    """Apply project-wide matplotlib + seaborn style.

    Idempotent — safe to call multiple times.
    """
    sns.set_theme(style="whitegrid", context="notebook")
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.family": "DejaVu Sans",
        }
    )

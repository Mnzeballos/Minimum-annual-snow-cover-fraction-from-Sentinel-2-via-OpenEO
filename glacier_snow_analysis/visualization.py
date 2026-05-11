"""
visualization.py
----------------
Plotting helpers for glacier snow-cover results.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_minimum_snow_cover(
    yearly_min: pd.DataFrame,
    glacier_name: str,
    output_path: str | Path | None = None,
    show: bool = True,
) -> plt.Figure:
    """
    Plot the minimum annual snow-cover fraction for a glacier.

    Parameters
    ----------
    yearly_min : pd.DataFrame
        Output of :func:`postprocessing.get_yearly_minimum`.
    glacier_name : str
        Human-readable name shown in the plot title.
    output_path : str | Path | None
        If provided, saves the figure to this path.
    show : bool
        If True, calls ``plt.show()`` after rendering.

    Returns
    -------
    matplotlib.figure.Figure
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    yearly_min["perc_snow"].plot(
        ax=ax,
        marker="o",
        color="red",
        label="Yearly minimum",
    )

    ax.set_title(f"Minimum annual snow cover — {glacier_name}")
    ax.set_ylabel("Snow cover (%)")
    ax.set_xlabel("Year")
    ax.legend()
    fig.tight_layout()

    if output_path is not None:
        fig.savefig(str(output_path), dpi=150)

    if show:
        plt.show()

    return fig

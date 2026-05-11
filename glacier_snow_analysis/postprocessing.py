"""
postprocessing.py
-----------------
Load, parse, and process the raw OpenEO JSON time series into a clean
Pandas DataFrame with snow-cover fractions and yearly aggregates.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def load_timeseries(json_path: str | Path) -> pd.DataFrame:
    """
    Load the raw pixel-count JSON produced by the OpenEO batch job.

    The JSON is expected to have date strings as keys, each mapping to a
    nested list: ``[[n_catchment, n_cloud, n_snow]]``.

    Parameters
    ----------
    json_path : str | Path
        Path to ``timeseries.json``.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by date with columns
        ``n_catchment_vals``, ``n_cloud_vals``, ``n_snow_vals``.
    """
    json_path = Path(json_path)
    with open(json_path, "r") as f:
        raw = json.load(f)

    dates = list(raw.keys())
    records = {
        "time": pd.to_datetime(dates),
        "n_catchment_vals": [raw[k][0][0] for k in dates],
        "n_cloud_vals":     [raw[k][0][1] for k in dates],
        "n_snow_vals":      [raw[k][0][2] for k in dates],
    }

    df = (
        pd.DataFrame(records)
        .set_index("time")
        .sort_index()
    )
    return df


def compute_snow_fractions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add ``perc_cloud`` and ``perc_snow`` columns (percentage of catchment
    area covered by clouds / snow) to the pixel-count DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Output of :func:`load_timeseries`.

    Returns
    -------
    pd.DataFrame
        Same DataFrame with two additional columns.
    """
    df = df.copy()
    df["perc_cloud"] = df["n_cloud_vals"] / df["n_catchment_vals"] * 100
    df["perc_snow"]  = df["n_snow_vals"]  / df["n_catchment_vals"] * 100
    return df


def get_yearly_minimum(
    df: pd.DataFrame,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """
    Resample the time series to annual frequency and return the minimum
    snow-cover fraction for each year.

    Parameters
    ----------
    df : pd.DataFrame
        Output of :func:`compute_snow_fractions`.
    output_path : str | Path | None
        If provided, saves the result as a CSV file at this path.

    Returns
    -------
    pd.DataFrame
        Annual minimum values.
    """
    yearly_min = df.resample("YE").min()

    if output_path is not None:
        yearly_min.to_csv(str(output_path))

    return yearly_min

"""Summary-statistics helpers shared by the tasks and the report writer."""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd


def describe_grid(values: np.ndarray) -> Mapping[str, float]:
    """Overall and terminal statistics of a ``(n_paths, n_steps + 1)`` grid."""
    grid = np.asarray(values, dtype=float)
    final = grid[:, -1]
    return {
        "Overall Mean": float(grid.mean()),
        "Overall Std Dev": float(grid.std(ddof=1)),
        "Overall Min": float(grid.min()),
        "Overall Max": float(grid.max()),
        "Mean Final": float(final.mean()),
        "Std Dev Final": float(final.std(ddof=1)),
    }


def describe_series(values: np.ndarray) -> Mapping[str, float]:
    """Mean/std/min/max of a 1-D sample."""
    sample = np.asarray(values, dtype=float).ravel()
    return {
        "Mean": float(sample.mean()),
        "Standard Deviation": float(sample.std(ddof=1)),
        "Minimum": float(sample.min()),
        "Maximum": float(sample.max()),
    }


def stats_table(columns: Mapping[str, Mapping[str, float]]) -> pd.DataFrame:
    """Assemble named statistic dictionaries into a tidy table."""
    frame = pd.DataFrame(columns)
    frame.index.name = "Statistic"
    return frame.reset_index()

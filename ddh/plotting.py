"""Figures for the results report.

Colours come from the validated categorical palette:
slot 1 blue ``#2a78d6``, slot 2 orange ``#eb6834``, slot 7 violet ``#4a3aa7``.
Only pairs that clear the CVD and normal-vision separation floors are ever put
in the same axes (blue/orange, blue/violet, orange/violet).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

BLUE = "#2a78d6"
ORANGE = "#eb6834"
VIOLET = "#4a3aa7"
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#e3e2dd"

_RC = {
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_MUTED,
    "axes.titlecolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10,
    "axes.grid": True,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "text.color": INK,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.frameon": False,
    "legend.fontsize": 9,
    "font.size": 10,
    "figure.dpi": 150,
    "lines.linewidth": 2.0,
}


def _save(fig: plt.Figure, path: Path | str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_simulated_paths(
    grid: np.ndarray,
    outfile: Path | str,
    title: str,
    ylabel: str,
    path_color: str = BLUE,
    mean_label: str = "Mean path",
    n_show: int = 100,
    seed: int = 0,
) -> Path:
    """Spaghetti plot of ``n_show`` sampled paths plus the full-sample mean.

    Two series: the sampled paths (thin, low alpha, one shared legend entry)
    and the mean across *all* paths (thick violet line).
    """
    grid = np.asarray(grid, dtype=float)
    rng = np.random.default_rng(seed)
    n_show = min(n_show, grid.shape[0])
    sample = rng.choice(grid.shape[0], size=n_show, replace=False)
    steps = np.arange(grid.shape[1])

    with plt.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(9, 4.6))
        ax.plot(steps, grid[sample].T, color=path_color, alpha=0.18, linewidth=0.7)
        ax.plot([], [], color=path_color, linewidth=2.0, label=f"{n_show} sampled paths")
        ax.plot(steps, grid.mean(axis=0), color=VIOLET, linewidth=2.0, label=mean_label)
        ax.set_title(title)
        ax.set_xlabel("Time step")
        ax.set_ylabel(ylabel)
        ax.set_xlim(steps[0], steps[-1])
        ax.grid(axis="x", alpha=0.35)
        ax.legend(loc="upper left")
        return _save(fig, outfile)


def plot_pnl_distribution(
    unhedged: np.ndarray,
    hedged: np.ndarray,
    outfile: Path | str,
    title: str = "Terminal P&L distribution: unhedged vs delta-hedged",
    bins: int = 60,
) -> Path:
    """Small multiples of the two terminal P&L distributions.

    The two samples differ by more than an order of magnitude in spread, so an
    overlay on a shared axis would collapse the hedged series into one bar.
    Each panel keeps its own x-scale and states its spread, and the shared
    zero reference line ties them together.
    """
    unhedged = np.asarray(unhedged, dtype=float).ravel()
    hedged = np.asarray(hedged, dtype=float).ravel()
    panels = [
        ("No hedge", unhedged, BLUE),
        ("Delta hedged", hedged, ORANGE),
    ]

    with plt.rc_context(_RC):
        fig, axes = plt.subplots(2, 1, figsize=(9, 6.0))
        for ax, (label, sample, color) in zip(axes, panels):
            ax.hist(sample, bins=bins, color=color, zorder=2)
            ax.axvline(0.0, color=INK_MUTED, linewidth=1.0,
                       linestyle=(0, (4, 3)), zorder=3)
            ax.set_ylabel("Number of paths")
            ax.grid(axis="x", alpha=0.35)
            ax.set_title(
                f"{label}   -   sd {sample.std(ddof=1):,.2f}, "
                f"range [{sample.min():,.2f}, {sample.max():,.2f}]",
                fontsize=10,
                loc="left",
            )
        axes[0].annotate(
            title,
            xy=(0, 1),
            xytext=(0, 34),
            xycoords="axes fraction",
            textcoords="offset points",
            fontsize=12,
            fontweight="bold",
            color=INK,
            va="bottom",
        )
        axes[-1].set_xlabel("Terminal P&L")
        return _save(fig, outfile)


def plot_pnl_paths(
    unhedged: np.ndarray,
    hedged: np.ndarray,
    outfile: Path | str,
    title: str,
    n_show: int = 100,
    seed: int = 0,
) -> Path:
    """Sampled P&L trajectories for both strategies on a shared scale."""
    unhedged = np.asarray(unhedged, dtype=float)
    hedged = np.asarray(hedged, dtype=float)
    rng = np.random.default_rng(seed)
    n_show = min(n_show, unhedged.shape[0])
    sample = rng.choice(unhedged.shape[0], size=n_show, replace=False)
    steps = np.arange(unhedged.shape[1])

    with plt.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(9, 4.6))
        ax.plot(steps, unhedged[sample].T, color=BLUE, alpha=0.16, linewidth=0.7)
        ax.plot(steps, hedged[sample].T, color=ORANGE, alpha=0.30, linewidth=0.7)
        ax.plot([], [], color=BLUE, linewidth=2.0, label="No hedge")
        ax.plot([], [], color=ORANGE, linewidth=2.0, label="Delta hedged")
        ax.axhline(0.0, color=INK_MUTED, linewidth=1.0, linestyle=(0, (4, 3)))
        ax.set_title(title)
        ax.set_xlabel("Time step")
        ax.set_ylabel("Running P&L")
        ax.set_xlim(steps[0], steps[-1])
        ax.grid(axis="x", alpha=0.35)
        ax.legend(loc="lower left")
        return _save(fig, outfile)


def plot_market_panels(
    frame: pd.DataFrame,
    outfile: Path | str,
    title: str,
) -> Path:
    """Small multiples of spot, option mid and implied vol over the window.

    Three measures on three different scales get three stacked panels sharing
    the date axis - never two y-axes on one plot.
    """
    panels = [
        ("spot", "Spot ($)", BLUE),
        ("market_price", "Option mid ($)", ORANGE),
        ("implied_vol", "Implied vol", VIOLET),
    ]
    with plt.rc_context(_RC):
        fig, axes = plt.subplots(3, 1, figsize=(9, 7.2), sharex=True)
        for ax, (col, label, color) in zip(axes, panels):
            ax.plot(frame.index, frame[col], color=color, marker="o", markersize=4)
            ax.set_ylabel(label)
            ax.grid(axis="x", alpha=0.35)
        axes[0].set_title(title)
        axes[-1].set_xlabel("Date")
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        fig.autofmt_xdate(rotation=0, ha="center")
        return _save(fig, outfile)


def plot_market_pnl(
    frame: pd.DataFrame,
    outfile: Path | str,
    title: str,
    annotate: Optional[Sequence[str]] = None,
) -> Path:
    """Hedged vs unhedged running P&L on the market path (same units, one axis)."""
    with plt.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(9, 4.6))
        ax.plot(frame.index, frame["pnl_no_hedge"], color=BLUE, marker="o",
                markersize=4, label="No hedge")
        ax.plot(frame.index, frame["pnl_hedge"], color=ORANGE, marker="o",
                markersize=4, label="Delta hedged")
        ax.axhline(0.0, color=INK_MUTED, linewidth=1.0, linestyle=(0, (4, 3)))

        # Direct labels on the terminal points instead of labelling every node.
        for col, color in (("pnl_no_hedge", BLUE), ("pnl_hedge", ORANGE)):
            x, y = frame.index[-1], frame[col].iloc[-1]
            ax.annotate(f"{y:,.1f}", xy=(x, y), xytext=(6, 0),
                        textcoords="offset points", va="center",
                        fontsize=9, color=INK_MUTED)

        if annotate:
            for stamp in annotate:
                ts = pd.Timestamp(stamp)
                if ts in frame.index:
                    ax.axvline(ts, color=GRID, linewidth=1.2, zorder=0)

        ax.set_title(title)
        ax.set_xlabel("Date")
        ax.set_ylabel("Running P&L ($ per contract)")
        ax.grid(axis="x", alpha=0.35)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.margins(x=0.06)
        ax.legend(loc="lower left")
        fig.autofmt_xdate(rotation=0, ha="center")
        return _save(fig, outfile)

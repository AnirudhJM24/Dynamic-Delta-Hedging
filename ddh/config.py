"""Run configuration for both tasks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Paths:
    """Input and output locations."""

    root: Path = PROJECT_ROOT
    spot_csv: Path = PROJECT_ROOT / "sec_GOOG.csv"
    rate_csv: Path = PROJECT_ROOT / "interest.csv"
    quotes_csv: Path = PROJECT_ROOT / "op_GOOG.csv"
    output_dir: Path = PROJECT_ROOT / "output"
    figures_dir: Path = PROJECT_ROOT / "output" / "figures"
    results_md: Path = PROJECT_ROOT / "results.md"


@dataclass(frozen=True)
class Task1Config:
    """Simulated delta-hedging experiment (report section 1)."""

    spot: float = 100.0
    strike: float = 105.0
    rate: float = 0.025
    maturity: float = 0.4
    volatility: float = 0.24
    steps: int = 100
    paths: int = 1000
    option_type: str = "C"
    seed: int = 42
    plot_paths: int = 100


@dataclass(frozen=True)
class Task2Config:
    """Market-data delta-hedging experiment (report section 2)."""

    ticker: str = "GOOG"
    strike: float = 500.0
    option_type: str = "C"
    expiry: str = "2011-09-17"
    start: str = "2011-07-05"
    end: str = "2011-07-29"
    # The C++ run treated the window end as exclusive, so the last observed
    # day is the trading day before ``end``.
    end_inclusive: bool = False
    trading_days_per_year: int = 252
    initial_vol_guess: float = 0.2
    # The original C++ run calibrated every day's implied volatility against
    # the *initial* time to maturity and then compressed the option's whole
    # remaining life into the observation window.  Both flags reproduce that
    # behaviour; set them to False for the economically consistent variant.
    iv_uses_initial_maturity: bool = True
    compress_maturity_to_window: bool = True
    # Distinguishes the outputs of alternative runs; "report" owns the
    # unsuffixed file names.
    variant: str = "report"
    make_figures: bool = True


@dataclass(frozen=True)
class RunConfig:
    paths_: Paths = field(default_factory=Paths)
    task1: Task1Config = field(default_factory=Task1Config)
    task2: Task2Config = field(default_factory=Task2Config)

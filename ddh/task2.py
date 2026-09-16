"""Task 2 - delta hedging a real GOOG call with market data.

Port of ``task2.cpp``: load spot, rates and option quotes, back out a daily
implied volatility from the mid-market quote, then run the same hedged /
unhedged P&L comparison along the realised market path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from .config import Paths, Task2Config
from .market_data import MarketData
from .option import Option
from .plotting import plot_market_panels, plot_market_pnl
from .pnl import PnLCalculator
from .pricing import OptionPricer
from .stats import describe_series, stats_table
from .storage import save_frame


@dataclass
class Task2Output:
    config: Task2Config
    option: Option
    frame: pd.DataFrame
    initial_maturity: float
    pnl_stats: pd.DataFrame
    figures: Dict[str, Path]
    csvs: Dict[str, Path]


def _implied_vols(
    frame: pd.DataFrame,
    pricer: OptionPricer,
    strike: float,
    iv_maturities: np.ndarray,
    guess: float,
) -> np.ndarray:
    vols = np.empty(len(frame))
    previous = guess
    for i, (_, row) in enumerate(frame.iterrows()):
        option = Option(
            strike=strike,
            spot=row["spot"],
            rate=row["rate"],
            maturity=float(iv_maturities[i]),
            volatility=previous,
        )
        vols[i] = pricer.implied_volatility(option, row["market_price"])
        previous = vols[i]
    return vols


def run(config: Task2Config, paths_cfg: Paths) -> Task2Output:
    market = MarketData.load(paths_cfg.spot_csv, paths_cfg.rate_csv, paths_cfg.quotes_csv)
    chain = market.option_chain(config.expiry, config.strike, config.option_type)
    frame = market.observation_frame(
        chain, config.start, config.end, end_inclusive=config.end_inclusive
    )

    expiry = pd.Timestamp(config.expiry)
    n_obs = len(frame)
    steps = n_obs - 1
    year = config.trading_days_per_year

    # True trading days left to expiry on each observation date.
    days_left = np.array(
        [market.trading_days_to(d, expiry) for d in frame.index], dtype=float
    )
    actual_maturity = days_left / year
    initial_maturity = float(actual_maturity[0])

    # Maturity used to back out implied vol.
    iv_maturities = (
        np.full(n_obs, initial_maturity)
        if config.iv_uses_initial_maturity
        else actual_maturity
    )

    # Maturity used when marking the book inside the hedging loop.
    hedge_maturities = (
        initial_maturity * (1.0 - np.arange(n_obs) / n_obs)
        if config.compress_maturity_to_window
        else actual_maturity
    )

    pricer = OptionPricer(config.option_type)
    implied_vol = _implied_vols(
        frame, pricer, config.strike, iv_maturities, config.initial_vol_guess
    )

    option = Option(
        strike=config.strike,
        spot=float(frame["spot"].iloc[0]),
        rate=float(frame["rate"].iloc[0]),
        maturity=initial_maturity,
        volatility=float(implied_vol[0]),
    )
    calculator = PnLCalculator(option, pricer, steps)
    result = calculator.run(
        frame["spot"].to_numpy()[None, :],
        rates=frame["rate"].to_numpy(),
        volatilities=implied_vol,
        maturities=hedge_maturities,
    )

    frame = frame.assign(
        days_to_expiry=days_left.astype(int),
        maturity_used=hedge_maturities,
        implied_vol=implied_vol,
        model_price=result.option_prices[0],
        delta=result.deltas[0],
        pnl_no_hedge=result.pnl_no_hedge[0],
        pnl_hedge=result.hedging_error[0],
    )

    pnl_stats = stats_table(
        {
            "PnL No Hedge": describe_series(frame["pnl_no_hedge"].to_numpy()),
            "PnL Hedge": describe_series(frame["pnl_hedge"].to_numpy()),
        }
    )

    suffix = "" if config.variant == "report" else f"_{config.variant}"
    export = frame.reset_index().rename(columns={"date": "Date"})
    csvs = {
        "task2_results": save_frame(
            export, paths_cfg.output_dir / f"task2_results{suffix}.csv"
        )
    }

    label = f"{config.ticker} {config.option_type} {config.strike:g} exp {config.expiry}"
    figures: Dict[str, Path] = {}
    if config.make_figures:
        figures["market"] = plot_market_panels(
            frame,
            paths_cfg.figures_dir / f"task2_market{suffix}.png",
            title=f"{label}: spot, mid quote and daily implied volatility",
        )
        figures["pnl"] = plot_market_pnl(
            frame,
            paths_cfg.figures_dir / f"task2_pnl{suffix}.png",
            title=f"{label}: running hedged vs unhedged P&L",
        )

    return Task2Output(
        config=config,
        option=option,
        frame=frame,
        initial_maturity=initial_maturity,
        pnl_stats=pnl_stats,
        figures=figures,
        csvs=csvs,
    )

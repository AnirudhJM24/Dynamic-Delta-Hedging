"""Task 1 - option pricing and P&L on simulated paths.

Port of ``task1.cpp``: simulate GBM stock paths, mark the option along each
path, and compare the terminal P&L of a naked short call against the same
position run with a discretely rebalanced delta hedge.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

from .config import Paths, Task1Config
from .option import Option
from .plotting import (
    BLUE,
    ORANGE,
    plot_pnl_distribution,
    plot_pnl_paths,
    plot_simulated_paths,
)
from .pnl import PnLCalculator, PnLResult
from .pricing import OptionPricer
from .simulation import StockPriceSimulator
from .stats import describe_grid, describe_series, stats_table
from .storage import save_to_csv


@dataclass
class Task1Output:
    config: Task1Config
    option: Option
    initial_price: float
    initial_delta: float
    paths: np.ndarray
    result: PnLResult
    price_stats: pd.DataFrame
    pnl_stats: pd.DataFrame
    figures: Dict[str, Path]
    csvs: Dict[str, Path]


def run(config: Task1Config, paths_cfg: Paths) -> Task1Output:
    option = Option(
        strike=config.strike,
        spot=config.spot,
        rate=config.rate,
        maturity=config.maturity,
        volatility=config.volatility,
    )
    pricer = OptionPricer(config.option_type)
    initial_price, initial_delta = pricer.bsm(option)

    simulator = StockPriceSimulator(option, config.paths, config.steps, seed=config.seed)
    stock_paths = simulator.simulate()

    calculator = PnLCalculator(option, pricer, config.steps)
    result = calculator.run(stock_paths)

    price_stats = stats_table(
        {
            "Stock Price": describe_grid(stock_paths),
            "Option Price": describe_grid(result.option_prices),
        }
    )
    pnl_stats = stats_table(
        {
            "PnL without Hedge": describe_series(result.final_pnl_no_hedge),
            "Hedging Error PnL": describe_series(result.final_hedging_error),
        }
    )

    out = paths_cfg.output_dir
    figs = paths_cfg.figures_dir
    csvs = {
        "stock_paths": save_to_csv(stock_paths, out / "stock_paths.csv"),
        "option_prices": save_to_csv(result.option_prices, out / "option_prices.csv"),
        "pnl_results": save_to_csv(
            np.column_stack([result.final_pnl_no_hedge, result.final_hedging_error]),
            out / "pnl_results_task1.csv",
            columns=["pnl_no_hedge", "hedging_error"],
        ),
    }

    figures = {
        "stock_paths": plot_simulated_paths(
            stock_paths,
            figs / "task1_stock_paths.png",
            title=f"Simulated stock price paths (showing {config.plot_paths} of {config.paths})",
            ylabel="Stock price ($)",
            path_color=BLUE,
            mean_label="Mean path (all paths)",
            n_show=config.plot_paths,
            seed=config.seed,
        ),
        "option_prices": plot_simulated_paths(
            result.option_prices,
            figs / "task1_option_prices.png",
            title=f"Simulated option price paths (showing {config.plot_paths} of {config.paths})",
            ylabel="Option price ($)",
            path_color=ORANGE,
            mean_label="Mean option price path",
            n_show=config.plot_paths,
            seed=config.seed,
        ),
        "pnl_paths": plot_pnl_paths(
            result.pnl_no_hedge,
            result.hedging_error,
            figs / "task1_pnl_paths.png",
            title=f"Running P&L along {config.plot_paths} sampled paths",
            n_show=config.plot_paths,
            seed=config.seed,
        ),
        "pnl_distribution": plot_pnl_distribution(
            result.final_pnl_no_hedge,
            result.final_hedging_error,
            figs / "task1_pnl_distribution.png",
            title=f"Terminal P&L over {config.paths} paths: unhedged vs delta-hedged",
        ),
    }

    return Task1Output(
        config=config,
        option=option,
        initial_price=initial_price,
        initial_delta=initial_delta,
        paths=stock_paths,
        result=result,
        price_stats=price_stats,
        pnl_stats=pnl_stats,
        figures=figures,
        csvs=csvs,
    )

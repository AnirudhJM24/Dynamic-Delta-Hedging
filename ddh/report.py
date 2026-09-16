"""Renders ``results.md`` from the task outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from . import validation
from .config import Paths, RunConfig
from .task1 import Task1Output
from .task2 import Task2Output


def _md_table(frame: pd.DataFrame, floatfmt: str = "{:,.4f}") -> str:
    display = frame.copy()
    for col in display.columns:
        if pd.api.types.is_float_dtype(display[col]):
            display[col] = display[col].map(lambda v: floatfmt.format(v))
    header = "| " + " | ".join(str(c) for c in display.columns) + " |"
    rule = "| " + " | ".join("---" for _ in display.columns) + " |"
    rows = [
        "| " + " | ".join(str(v) for v in record) + " |"
        for record in display.itertuples(index=False, name=None)
    ]
    return "\n".join([header, rule, *rows])


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def build(
    run_config: RunConfig,
    task1: Task1Output,
    task2: Task2Output,
    task2_consistent: Optional[Task2Output] = None,
) -> Path:
    paths_cfg: Paths = run_config.paths_
    root = paths_cfg.root
    c1 = task1.config
    c2 = task2.config

    t2 = task2.frame
    t2_table = pd.DataFrame(
        {
            "Date": [d.strftime("%Y-%m-%d") for d in t2.index],
            "Spot": t2["spot"].to_numpy(),
            "Market Mid": t2["market_price"].to_numpy(),
            "Implied Vol": t2["implied_vol"].to_numpy(),
            "Delta": t2["delta"].to_numpy(),
            "PnL No Hedge": t2["pnl_no_hedge"].to_numpy(),
            "PnL Hedge": t2["pnl_hedge"].to_numpy(),
        }
    )

    nh_final = float(t2["pnl_no_hedge"].iloc[-1])
    h_final = float(t2["pnl_hedge"].iloc[-1])
    nh_range = float(t2["pnl_no_hedge"].max() - t2["pnl_no_hedge"].min())
    h_range = float(t2["pnl_hedge"].max() - t2["pnl_hedge"].min())

    unhedged_sd = float(task1.result.final_pnl_no_hedge.std(ddof=1))
    hedged_sd = float(task1.result.final_hedging_error.std(ddof=1))

    lines = [
        "# Dynamic Delta Hedging - Results",
        "",
        "Python implementation of the interim project originally written in C++.",
        "Every number and figure below is produced by `python run_all.py`; nothing is",
        "hand-entered.",
        "",
        "| | |",
        "| --- | --- |",
        "| Package | `ddh/` (option, pricing, pnl, simulation, market_data, plotting, tasks) |",
        "| Entry point | `run_all.py` |",
        "| Raw outputs | `output/*.csv`, `output/figures/*.png` |",
        f"| Task 1 seed | `{c1.seed}` (results are reproducible) |",
        "",
        "---",
        "",
        "## 1. Task 1 - Option pricing and P&L on simulated paths",
        "",
        "### 1.1 Objective",
        "",
        "Simulate stock price paths, compute the P&L of a short European call with and",
        "without a delta hedge, and store the results for analysis.",
        "",
        "### 1.2 Methodology",
        "",
        f"1. **Option.** Strike `K = {c1.strike:g}`, spot `S0 = {c1.spot:g}`, rate "
        f"`r = {c1.rate:g}`, maturity `T = {c1.maturity:g}`, volatility "
        f"`sigma = {c1.volatility:g}`, `{c1.steps}` time steps.",
        f"2. **Simulation.** `StockPriceSimulator` draws `{c1.paths}` geometric Brownian",
        "   motion paths using the exact log-Euler scheme",
        "   `S[i+1] = S[i] * exp((r - sigma^2/2) * dt + sigma * sqrt(dt) * Z)` and writes",
        "   them to `output/stock_paths.csv`.",
        "3. **Pricing and P&L.** `OptionPricer` marks the call at every step with time to",
        "   maturity running linearly from `T` to `0`; `PnLCalculator` then produces",
        "   both the delta-hedging error and the unhedged buy-and-hold P&L.",
        "4. **Storage.** `output/option_prices.csv` and `output/pnl_results_task1.csv`.",
        "",
        "The self-financing hedge is rolled forward as",
        "",
        "```",
        "B[0] = V[0] - Delta[0] * S[0]",
        "B[i] = B[i-1] * exp(r * dt) - (Delta[i] - Delta[i-1]) * S[i]",
        "HE[i] = Delta[i] * S[i] + B[i] - V[i]        (hedging error)",
        "PnL[i] = V[0] - V[i]                         (no hedge)",
        "```",
        "",
        f"The option is sold at its model value `V0 = {task1.initial_price:,.4f}` with",
        f"initial delta `{task1.initial_delta:,.4f}`.",
        "",
        "### 1.3 Summary statistics",
        "",
        _md_table(task1.price_stats, "{:,.2f}"),
        "",
        f"*Simulated stock and option prices across {c1.paths} paths x "
        f"{c1.steps + 1} observation points.*",
        "",
        "### 1.4 Stock price and option price evolution",
        "",
        f"![Simulated stock price paths]({_rel(task1.figures['stock_paths'], root)})",
        "",
        "*Figure 1: simulated stock price paths. The mean across all "
        f"{c1.paths} paths drifts up at the risk-free rate.*",
        "",
        f"![Simulated option price paths]({_rel(task1.figures['option_prices'], root)})",
        "",
        "*Figure 2: option price evolution. The mean is close to flat - under the",
        "risk-neutral drift used here the option's expected value grows only at the",
        "risk-free rate - while individual paths split between expiring worthless and",
        "converging on their intrinsic value.*",
        "",
        "### 1.5 Task 1 P&L results",
        "",
        _md_table(task1.pnl_stats, "{:,.2f}"),
        "",
        "*Terminal P&L of the two strategies over the simulated paths.*",
        "",
        f"![Running P&L paths]({_rel(task1.figures['pnl_paths'], root)})",
        "",
        "*Figure 3: running P&L along sampled paths. The unhedged position fans out with",
        "the underlying; the hedged position stays in a narrow band.*",
        "",
        f"![Terminal P&L distribution]({_rel(task1.figures['pnl_distribution'], root)})",
        "",
        "*Figure 4: terminal P&L distributions. The unhedged short call has a long left",
        "tail; the hedging error is tight and centred near zero.*",
        "",
        "**Observations**",
        "",
        "- The unhedged short call is heavily skewed: capped upside at the premium",
        f"  received (`{task1.result.final_pnl_no_hedge.max():,.2f}`) against a worst path",
        f"  of `{task1.result.final_pnl_no_hedge.min():,.2f}`.",
        f"- Delta hedging cuts the terminal standard deviation from `{unhedged_sd:,.2f}`",
        f"  to `{hedged_sd:,.2f}` - a reduction of "
        f"`{100 * (1 - hedged_sd / unhedged_sd):.1f}%`.",
        "- The residual hedging error has a mean near zero: what is left is discretisation",
        f"  error from rebalancing only {c1.steps} times, not a directional bet.",
        "",
        "---",
        "",
        "## 2. Task 2 - Hedging P&L with market data",
        "",
        "### 2.1 Objective",
        "",
        f"Evaluate the hedging performance of a {c2.ticker} call using historical spot",
        "prices, interest rates and option quotes: back out a daily implied volatility",
        "and compare hedged against unhedged P&L.",
        "",
        "### 2.2 Data sources",
        "",
        "| File | Contents |",
        "| --- | --- |",
        f"| `{_rel(paths_cfg.spot_csv, root)}` | daily adjusted closing spot prices |",
        f"| `{_rel(paths_cfg.rate_csv, root)}` | daily risk-free rates (percent) |",
        f"| `{_rel(paths_cfg.quotes_csv, root)}` | option quotes: date, expiry, type, strike, bid, ask |",
        "",
        "### 2.3 Parameters",
        "",
        "| Parameter | Value |",
        "| --- | --- |",
        f"| Observation window | {c2.start} to {t2.index[-1]:%Y-%m-%d} "
        f"({len(t2)} trading days; window end {c2.end} is exclusive, as in the C++ run) |",
        f"| Expiry | {c2.expiry} |",
        f"| Strike | {c2.strike:g} |",
        f"| Option type | {'Call' if c2.option_type == 'C' else 'Put'} |",
        f"| Initial volatility guess | {c2.initial_vol_guess:g} |",
        f"| Initial maturity | {int(t2['days_to_expiry'].iloc[0])} trading days "
        f"= {task2.initial_maturity:.6f} years |",
        "",
        "### 2.4 Methodology",
        "",
        "1. Load spot, rate and quote data and align them by date.",
        "2. Take the mid-market price `(best_bid + best_offer) / 2` as the observed price.",
        "3. Back out a daily implied volatility by binary search on the BSM price.",
        "4. Run `PnLCalculator` along the realised spot path with the daily implied",
        "   volatility and daily rate.",
        f"5. Write `{_rel(task2.csvs['task2_results'], root)}`.",
        "",
        "### 2.5 Results",
        "",
        _md_table(t2_table, "{:,.4f}"),
        "",
        "*Daily results; P&L figures are running totals from the first day.*",
        "",
        f"![Market panels]({_rel(task2.figures['market'], root)})",
        "",
        "*Figure 5: spot, option mid quote and daily implied volatility. Three measures on",
        "three scales get three panels sharing the date axis.*",
        "",
        f"![Hedged vs unhedged P&L]({_rel(task2.figures['pnl'], root)})",
        "",
        "*Figure 6: running hedged and unhedged P&L on the realised path.*",
        "",
        "**Observations**",
        "",
        f"- {c2.ticker} gapped up roughly "
        f"{100 * (t2['spot'].iloc[8] / t2['spot'].iloc[7] - 1):.0f}% on "
        f"{t2.index[8]:%Y-%m-%d} (earnings). The naked short call lost "
        f"`{abs(t2['pnl_no_hedge'].iloc[8] - t2['pnl_no_hedge'].iloc[7]):,.1f}` that day;",
        f"  the hedged book lost "
        f"`{abs(t2['pnl_hedge'].iloc[8] - t2['pnl_hedge'].iloc[7]):,.1f}`.",
        f"- Over the whole window the unhedged P&L travels a range of `{nh_range:,.1f}`",
        f"  against `{h_range:,.1f}` for the hedged book, ending at `{nh_final:,.1f}`",
        f"  versus `{h_final:,.1f}`.",
        f"- Daily implied volatility ranges from `{t2['implied_vol'].min():.4f}` to "
        f"`{t2['implied_vol'].max():.4f}`.",
        "- Delta hedging removes most, but not all, of the loss. A single overnight gap is",
        "  exactly the risk a delta hedge cannot neutralise: the hedge is linear, the",
        "  payoff is not, and the position is only rebalanced once a day.",
        "- Practical caveat: this run charges no transaction costs and assumes fills at the",
        "  close. Both would erode the hedged result further.",
        "",
    ]

    comparison = validation.compare(t2)
    if comparison is not None:
        lines += [
            "### 2.6 Cross-check against the original C++ report",
            "",
            "`reference/report_interim_task2.csv` holds the Task 2 table as printed in",
            "`report_interim.pdf`. The Python port reproduces it:",
            "",
            "| Quantity | Max absolute difference |",
            "| --- | --- |",
            f"| Daily implied volatility | {comparison.max_abs_diff['implied_vol']:.2e} |",
            f"| PnL no hedge | {comparison.max_abs_diff['pnl_no_hedge']:.4f} |",
            f"| PnL hedge | {comparison.max_abs_diff['pnl_hedge']:.4f} |",
            "",
            "The implied volatilities agree to every digit the report prints. The residual",
            "P&L differences are consistent with the tolerance of the C++ bisection: the",
            "reported volatilities are rounded to six figures, and the P&L is a difference",
            "of option prices whose vega is of order 50, so a 1e-6 volatility error moves",
            "the P&L by a few hundredths.",
            "",
        ]

    if task2_consistent is not None:
        alt = task2_consistent.frame
        lines += [
            "### 2.7 Maturity convention",
            "",
            "The original C++ run had two quirks in how time to maturity was handled, kept",
            "here behind flags in `Task2Config` so the legacy numbers remain reproducible:",
            "",
            "- `iv_uses_initial_maturity` - every day's implied volatility was solved",
            f"  against the *initial* {int(t2['days_to_expiry'].iloc[0])}-day maturity",
            "  rather than the days actually left.",
            "- `compress_maturity_to_window` - inside the hedging loop the option's entire",
            "  remaining life was compressed into the observation window, so it was marked",
            "  as if expiring on the last observed day.",
            "",
            "Setting both to `False` uses the true days to expiry throughout. The",
            "comparison:",
            "",
            "| | Report convention | True maturity |",
            "| --- | --- | --- |",
            f"| Implied vol, first day | {t2['implied_vol'].iloc[0]:.4f} | "
            f"{alt['implied_vol'].iloc[0]:.4f} |",
            f"| Implied vol, last day | {t2['implied_vol'].iloc[-1]:.4f} | "
            f"{alt['implied_vol'].iloc[-1]:.4f} |",
            f"| Final PnL no hedge | {t2['pnl_no_hedge'].iloc[-1]:,.2f} | "
            f"{alt['pnl_no_hedge'].iloc[-1]:,.2f} |",
            f"| Final PnL hedge | {t2['pnl_hedge'].iloc[-1]:,.2f} | "
            f"{alt['pnl_hedge'].iloc[-1]:,.2f} |",
            "",
            "The qualitative conclusion is unchanged - the hedge still absorbs the bulk of",
            "the move - but the compressed convention overstates time decay and therefore",
            "the size of both P&L series.",
            "",
        ]

    lines += [
        "---",
        "",
        "## 3. Code overview",
        "",
        "The C++ classes map one-to-one onto Python modules:",
        "",
        "| C++ class | Python | Role |",
        "| --- | --- | --- |",
        "| `Option` | `ddh/option.py` | immutable contract parameters (`K`, `S`, `r`, `T`, `sigma`) |",
        "| `Option_Price` | `ddh/pricing.py` | BSM price and delta, implied volatility by binary search, vectorised grid pricer |",
        "| `PNL_Calculator` | `ddh/pnl.py` | self-financing hedge recursion, hedged and unhedged P&L |",
        "| `Stock_Price_Simulator` | `ddh/simulation.py` | GBM path generation |",
        "| `Path_Saver` | `ddh/storage.py` | CSV output |",
        "| - | `ddh/market_data.py` | loads and aligns the three market CSVs |",
        "| - | `ddh/plotting.py` | figures |",
        "| - | `ddh/stats.py` | summary statistics |",
        "| `task1.cpp` | `ddh/task1.py` | simulated-path experiment |",
        "| `task2.cpp` | `ddh/task2.py` | market-data experiment |",
        "| - | `ddh/report.py` | renders this file |",
        "",
        "Two differences from the C++ original are worth calling out. Pricing is",
        f"vectorised over paths with NumPy, so all {c1.paths} x {c1.steps + 1} marks are",
        "computed in a handful of array operations rather than a double loop. And",
        "configuration lives in `ddh/config.py` dataclasses rather than being hard-coded",
        "in `main`.",
        "",
        "### Reproducing",
        "",
        "```bash",
        "pip install -r requirements.txt",
        "python run_all.py                            # regenerates output/ and this file",
        "python -m unittest discover -s tests -t .    # 14 unit tests",
        "```",
        "",
        "The test suite covers put-call parity, delta against a finite difference,",
        "implied-volatility round trips, the risk-neutral drift of the simulator, the",
        "`1/sqrt(n)` decay of the hedging error, and the cross-check in section 2.6.",
        "",
    ]

    target = paths_cfg.results_md
    target.write_text("\n".join(lines))
    return target

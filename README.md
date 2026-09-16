# Dynamic Delta Hedging

Python implementation of the interim project originally written in C++
(`report_interim.pdf`). It prices a European call with Black-Scholes-Merton,
runs a discretely rebalanced delta hedge, and compares the resulting P&L
against holding the option naked - first on simulated paths, then on real
GOOG market data.

## Running

```bash
pip install -r requirements.txt
python run_all.py                            # writes output/ and results.md
python -m unittest discover -s tests -t .    # unit tests
```

`run_all.py` takes `--seed`, `--paths`, `--steps` and
`--no-consistent-variant`.

## Layout

```
ddh/
  option.py       Option      - immutable contract parameters
  pricing.py      OptionPricer- BSM price/delta, implied vol by binary search
  pnl.py          PnLCalculator - self-financing hedge recursion, both P&L series
  simulation.py   StockPriceSimulator - GBM paths
  market_data.py  MarketData  - loads and aligns the three market CSVs
  storage.py      CSV output
  stats.py        summary statistics
  plotting.py     figures
  validation.py   cross-check against the C++ report's published table
  config.py       Paths / Task1Config / Task2Config dataclasses
  task1.py        simulated-path experiment
  task2.py        market-data experiment
  report.py       renders results.md
run_all.py        entry point
tests/            unit tests
reference/        Task 2 table transcribed from report_interim.pdf
```

Each module maps onto one of the original C++ classes; see section 3 of
[`results.md`](results.md) for the full correspondence.

## Inputs

| File | Contents |
| --- | --- |
| `sec_GOOG.csv` | daily adjusted closing spot prices |
| `interest.csv` | daily risk-free rates (percent) |
| `op_GOOG.csv` | option quotes (date, expiry, type, strike, bid, ask) |

## Outputs

`results.md` is the generated report. Raw data lands in `output/`:
`stock_paths.csv`, `option_prices.csv`, `pnl_results_task1.csv`,
`task2_results.csv`, and figures under `output/figures/`.

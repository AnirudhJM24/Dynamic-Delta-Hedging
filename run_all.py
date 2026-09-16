#!/usr/bin/env python3
"""Run both tasks end to end and regenerate ``results.md``.

    python run_all.py [--seed N] [--paths N] [--no-consistent-variant]
"""

from __future__ import annotations

import argparse
import dataclasses
import sys
import time

from ddh import report
from ddh.config import Paths, RunConfig, Task1Config, Task2Config
from ddh import task1 as task1_module
from ddh import task2 as task2_module


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=Task1Config.seed,
                        help="RNG seed for the Task 1 simulation")
    parser.add_argument("--paths", type=int, default=Task1Config.paths,
                        help="number of simulated paths in Task 1")
    parser.add_argument("--steps", type=int, default=Task1Config.steps,
                        help="number of time steps in Task 1")
    parser.add_argument("--no-consistent-variant", action="store_true",
                        help="skip the true-maturity Task 2 comparison")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    started = time.perf_counter()

    config = RunConfig(
        paths_=Paths(),
        task1=Task1Config(seed=args.seed, paths=args.paths, steps=args.steps),
        task2=Task2Config(),
    )
    config.paths_.output_dir.mkdir(parents=True, exist_ok=True)
    config.paths_.figures_dir.mkdir(parents=True, exist_ok=True)

    print("Task 1: simulating paths and computing P&L ...")
    out1 = task1_module.run(config.task1, config.paths_)
    print(f"  V0 = {out1.initial_price:.4f}, delta0 = {out1.initial_delta:.4f}")
    print(f"  terminal P&L sd: no hedge {out1.result.final_pnl_no_hedge.std(ddof=1):.4f}"
          f" / hedged {out1.result.final_hedging_error.std(ddof=1):.4f}")

    print("Task 2: calibrating implied vol and hedging the market path ...")
    out2 = task2_module.run(config.task2, config.paths_)
    print(f"  {len(out2.frame)} observation days,"
          f" implied vol {out2.frame['implied_vol'].min():.4f}"
          f"-{out2.frame['implied_vol'].max():.4f}")
    print(f"  final P&L: no hedge {out2.frame['pnl_no_hedge'].iloc[-1]:.4f}"
          f" / hedged {out2.frame['pnl_hedge'].iloc[-1]:.4f}")

    out2_consistent = None
    if not args.no_consistent_variant:
        print("Task 2 variant: true time to expiry ...")
        alt_config = dataclasses.replace(
            config.task2,
            iv_uses_initial_maturity=False,
            compress_maturity_to_window=False,
            variant="true_maturity",
            make_figures=False,
        )
        out2_consistent = task2_module.run(alt_config, config.paths_)
        print(f"  final P&L: no hedge"
              f" {out2_consistent.frame['pnl_no_hedge'].iloc[-1]:.4f}"
              f" / hedged {out2_consistent.frame['pnl_hedge'].iloc[-1]:.4f}")

    target = report.build(config, out1, out2, out2_consistent)
    elapsed = time.perf_counter() - started
    print(f"Wrote {target} in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

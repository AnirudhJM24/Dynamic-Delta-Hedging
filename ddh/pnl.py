"""Hedged and unhedged P&L along a price path.

Python port of the C++ ``PNL_Calculator`` class.

Convention
----------
The trader is **short** one option, sold at the model value observed at the
first step, and runs a self-financing delta hedge:

``B_0 = V_0 - Delta_0 * S_0``

``B_i = B_{i-1} * exp(r_{i-1} * dt) - (Delta_i - Delta_{i-1}) * S_i``

The *hedging error* at step ``i`` is the value of the replicating portfolio
net of the option's mark:

``HE_i = Delta_i * S_i + B_i - V_i``

The *unhedged* P&L is the mark-to-market of the naked short position:

``PnL_i = V_0 - V_i``
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .option import Option
from .pricing import OptionPricer


@dataclass
class PnLResult:
    """Per-step outputs of a hedging simulation."""

    option_prices: np.ndarray  # (n_paths, n_steps + 1)
    deltas: np.ndarray  # (n_paths, n_steps + 1)
    hedging_error: np.ndarray  # (n_paths, n_steps + 1)
    pnl_no_hedge: np.ndarray  # (n_paths, n_steps + 1)
    maturities: np.ndarray  # (n_steps + 1,)

    @property
    def final_hedging_error(self) -> np.ndarray:
        return self.hedging_error[:, -1]

    @property
    def final_pnl_no_hedge(self) -> np.ndarray:
        return self.pnl_no_hedge[:, -1]


class PnLCalculator:
    """Computes hedging error and buy-and-hold P&L along price paths."""

    def __init__(self, option: Option, pricer: OptionPricer, steps: int) -> None:
        if steps < 1:
            raise ValueError("steps must be >= 1")
        self.option = option
        self.pricer = pricer
        self.steps = steps

    # -- maturity schedule -------------------------------------------------
    def maturity_schedule(self) -> np.ndarray:
        """Time to maturity at each of the ``steps + 1`` observation points.

        Runs linearly from ``option.maturity`` down to zero, i.e. the path is
        assumed to be sampled from inception to expiry in ``steps`` intervals.
        """
        return self.option.maturity * (1.0 - np.arange(self.steps + 1) / self.steps)

    @property
    def dt(self) -> float:
        return self.option.maturity / self.steps

    # -- main entry point --------------------------------------------------
    def run(
        self,
        paths: np.ndarray,
        rates: Optional[np.ndarray] = None,
        volatilities: Optional[np.ndarray] = None,
        maturities: Optional[np.ndarray] = None,
    ) -> PnLResult:
        """Price the option along ``paths`` and compute both P&L series.

        Parameters
        ----------
        paths:
            Spot prices, shape ``(n_paths, steps + 1)``.  A 1-D array is
            treated as a single path.
        rates, volatilities:
            Scalars, or per-step arrays of length ``steps + 1``.  Default to
            the values carried by ``self.option``.
        maturities:
            Per-step time to maturity; defaults to :meth:`maturity_schedule`.
        """
        S = np.atleast_2d(np.asarray(paths, dtype=float))
        if S.shape[1] != self.steps + 1:
            raise ValueError(
                f"paths must have {self.steps + 1} columns, got {S.shape[1]}"
            )

        T = self.maturity_schedule() if maturities is None else np.asarray(maturities, float)
        r = self.option.rate if rates is None else rates
        sigma = self.option.volatility if volatilities is None else volatilities

        V, delta = self.pricer.price_grid(S, self.option.strike, r, T, sigma)

        hedging_error = self._hedging_error(S, V, delta, r)
        pnl_no_hedge = V[:, [0]] - V

        return PnLResult(
            option_prices=V,
            deltas=delta,
            hedging_error=hedging_error,
            pnl_no_hedge=pnl_no_hedge,
            maturities=T,
        )

    # -- pieces kept separate for parity with the C++ methods --------------
    def _hedging_error(
        self,
        S: np.ndarray,
        V: np.ndarray,
        delta: np.ndarray,
        rates,
    ) -> np.ndarray:
        """Self-financing replication error, rolled forward step by step."""
        n_steps = S.shape[1] - 1
        r = np.broadcast_to(np.atleast_1d(np.asarray(rates, dtype=float)), (n_steps + 1,))
        dt = self.dt

        error = np.zeros_like(S)
        bank = V[:, 0] - delta[:, 0] * S[:, 0]
        for i in range(1, n_steps + 1):
            bank = bank * np.exp(r[i - 1] * dt) - (delta[:, i] - delta[:, i - 1]) * S[:, i]
            error[:, i] = delta[:, i] * S[:, i] + bank - V[:, i]
        return error

    def calculate_hedging_error(self, paths: np.ndarray, **kwargs) -> np.ndarray:
        """Hedging-error series (C++ ``calculate_hedging_error``)."""
        return self.run(paths, **kwargs).hedging_error

    def calculate_pnl_no_hedge(self, paths: np.ndarray, **kwargs) -> np.ndarray:
        """Unhedged P&L series (C++ ``calculate_pnl_no_hedge``)."""
        return self.run(paths, **kwargs).pnl_no_hedge

    def get_option_prices(self, paths: np.ndarray, **kwargs) -> np.ndarray:
        """Option marks along the path (C++ ``get_option_prices``)."""
        return self.run(paths, **kwargs).option_prices

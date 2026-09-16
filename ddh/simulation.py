"""Geometric Brownian motion path generator.

Python port of the C++ ``Stock_Price_Simulator`` class.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from .option import Option


class StockPriceSimulator:
    """Generates GBM stock price paths under the option's parameters.

    The paths use the exact log-Euler solution

    ``S_{i+1} = S_i * exp((r - sigma^2 / 2) * dt + sigma * sqrt(dt) * Z)``

    with ``dt = T / n_steps`` and ``Z ~ N(0, 1)``.
    """

    def __init__(
        self,
        option: Option,
        n_paths: int,
        n_steps: int,
        seed: Optional[int] = None,
    ) -> None:
        if n_paths < 1 or n_steps < 1:
            raise ValueError("n_paths and n_steps must be >= 1")
        self.option = option
        self.n_paths = n_paths
        self.n_steps = n_steps
        self.rng = np.random.default_rng(seed)

    @property
    def dt(self) -> float:
        return self.option.maturity / self.n_steps

    def simulate(self) -> np.ndarray:
        """Return an array of shape ``(n_paths, n_steps + 1)``."""
        sigma = self.option.volatility
        drift = (self.option.rate - 0.5 * sigma**2) * self.dt
        diffusion = sigma * np.sqrt(self.dt)

        shocks = self.rng.standard_normal((self.n_paths, self.n_steps))
        log_increments = drift + diffusion * shocks

        paths = np.empty((self.n_paths, self.n_steps + 1), dtype=float)
        paths[:, 0] = self.option.spot
        paths[:, 1:] = self.option.spot * np.exp(np.cumsum(log_increments, axis=1))
        return paths

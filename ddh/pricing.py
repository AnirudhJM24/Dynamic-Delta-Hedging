"""Black-Scholes-Merton pricing and implied volatility.

Python port of the C++ ``Option_Price`` class.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np
from scipy.stats import norm

from .option import Option

CALL = "C"
PUT = "P"


class OptionPricer:
    """BSM pricer for a single option type (``"C"`` or ``"P"``)."""

    def __init__(self, flag: str = CALL) -> None:
        flag = flag.upper()
        if flag not in (CALL, PUT):
            raise ValueError(f"option flag must be 'C' or 'P', got {flag!r}")
        self.flag = flag

    @property
    def is_call(self) -> bool:
        return self.flag == CALL

    # -- pricing ----------------------------------------------------------
    def bsm(self, option: Option) -> Tuple[float, float]:
        """Return ``(price, delta)`` for ``option``.

        Handles the degenerate cases of zero time to maturity and zero
        volatility by falling back on the discounted intrinsic value.
        """
        S = option.spot
        K = option.strike
        r = option.rate
        T = option.maturity
        sigma = option.volatility

        if T <= 0.0 or sigma <= 0.0 or S <= 0.0:
            if self.is_call:
                intrinsic = max(S - K * math.exp(-r * max(T, 0.0)), 0.0)
                delta = 1.0 if S > K else 0.0
            else:
                intrinsic = max(K * math.exp(-r * max(T, 0.0)) - S, 0.0)
                delta = -1.0 if S < K else 0.0
            return intrinsic, delta

        vol_sqrt_t = sigma * math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / vol_sqrt_t
        d2 = d1 - vol_sqrt_t
        df = math.exp(-r * T)

        if self.is_call:
            price = S * norm.cdf(d1) - K * df * norm.cdf(d2)
            delta = norm.cdf(d1)
        else:
            price = K * df * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = norm.cdf(d1) - 1.0
        return price, delta

    def price(self, option: Option) -> float:
        return self.bsm(option)[0]

    def delta(self, option: Option) -> float:
        return self.bsm(option)[1]

    # -- vectorised helper used by the simulations ------------------------
    def price_grid(
        self,
        spots: np.ndarray,
        strike: float,
        rates,
        maturities,
        volatilities,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Vectorised ``(price, delta)`` over a grid of spot values.

        ``spots`` has shape ``(n_paths, n_steps + 1)``.  ``rates``,
        ``maturities`` and ``volatilities`` are scalars or arrays of shape
        ``(n_steps + 1,)`` and are broadcast across the path dimension, so
        both the constant-parameter simulation (Task 1) and the
        day-by-day market calibration (Task 2) share this code path.
        """
        S = np.asarray(spots, dtype=float)
        K = float(strike)
        r = np.broadcast_to(np.atleast_1d(np.asarray(rates, dtype=float)), (S.shape[1],))[None, :]
        T = np.broadcast_to(np.atleast_1d(np.asarray(maturities, dtype=float)), (S.shape[1],))[None, :]
        sigma = np.broadcast_to(
            np.atleast_1d(np.asarray(volatilities, dtype=float)), (S.shape[1],)
        )[None, :]

        live = np.broadcast_to((T > 0.0) & (sigma > 0.0), S.shape)
        with np.errstate(divide="ignore", invalid="ignore"):
            safe_T = np.where(T > 0.0, T, 1.0)
            safe_sigma = np.where(sigma > 0.0, sigma, 1.0)
            vol_sqrt_t = safe_sigma * np.sqrt(safe_T)
            d1 = (np.log(S / K) + (r + 0.5 * safe_sigma**2) * safe_T) / vol_sqrt_t
            d2 = d1 - vol_sqrt_t
            df = np.exp(-r * safe_T)
            if self.is_call:
                live_price = S * norm.cdf(d1) - K * df * norm.cdf(d2)
                live_delta = norm.cdf(d1)
                dead_price = np.maximum(S - K, 0.0)
                dead_delta = (S > K).astype(float)
            else:
                live_price = K * df * norm.cdf(-d2) - S * norm.cdf(-d1)
                live_delta = norm.cdf(d1) - 1.0
                dead_price = np.maximum(K - S, 0.0)
                dead_delta = -(S < K).astype(float)

        price = np.where(live, live_price, np.broadcast_to(dead_price, S.shape))
        delta = np.where(live, live_delta, np.broadcast_to(dead_delta, S.shape))
        return price, delta

    # -- calibration ------------------------------------------------------
    def implied_volatility(
        self,
        option: Option,
        market_price: float,
        lower: float = 1e-6,
        upper: float = 3.0,
        tol: float = 1e-8,
        max_iter: int = 200,
    ) -> float:
        """Implied volatility by binary search, mirroring the C++ routine.

        The market price is first clamped into the range achievable by the
        model on ``[lower, upper]`` so the bisection always brackets a root.
        """
        lo_price = self.bsm(option.with_(volatility=lower))[0]
        hi_price = self.bsm(option.with_(volatility=upper))[0]
        target = min(max(float(market_price), lo_price), hi_price)

        lo, hi = lower, upper
        for _ in range(max_iter):
            mid = 0.5 * (lo + hi)
            value = self.bsm(option.with_(volatility=mid))[0]
            if abs(value - target) < tol or (hi - lo) < tol:
                return mid
            if value < target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

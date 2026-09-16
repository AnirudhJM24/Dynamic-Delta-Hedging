"""Loading and aligning the GOOG market data used by Task 2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class MarketData:
    """Spot prices, risk-free rates and option quotes, aligned by date."""

    spot: pd.Series  # indexed by date, close_adj
    rate: pd.Series  # indexed by date, decimal rate
    quotes: pd.DataFrame  # date, exdate, cp_flag, strike_price, best_bid, best_offer

    @classmethod
    def load(
        cls,
        spot_csv: Path | str,
        rate_csv: Path | str,
        quotes_csv: Path | str,
    ) -> "MarketData":
        spot = (
            pd.read_csv(spot_csv, parse_dates=["date"])
            .set_index("date")["close_adj"]
            .sort_index()
        )
        rate = (
            pd.read_csv(rate_csv, parse_dates=["date"])
            .set_index("date")["rate(%)"]
            .sort_index()
            / 100.0
        )
        quotes = pd.read_csv(quotes_csv, parse_dates=["date", "exdate"])
        return cls(spot=spot, rate=rate, quotes=quotes)

    # -- helpers -----------------------------------------------------------
    def option_chain(
        self,
        expiry: str | pd.Timestamp,
        strike: float,
        cp_flag: str = "C",
    ) -> pd.DataFrame:
        """Mid-market quote series for one contract, indexed by date."""
        expiry = pd.Timestamp(expiry)
        chain = self.quotes[
            (self.quotes["exdate"] == expiry)
            & (self.quotes["cp_flag"] == cp_flag)
            & (self.quotes["strike_price"] == strike)
        ].copy()
        if chain.empty:
            raise ValueError(
                f"no quotes for {cp_flag} {strike} expiring {expiry.date()}"
            )
        chain["market_price"] = 0.5 * (chain["best_bid"] + chain["best_offer"])
        return chain.set_index("date").sort_index()

    def trading_days_to(self, start: pd.Timestamp, expiry: pd.Timestamp) -> int:
        """Number of trading days in ``[start, expiry)`` per the spot calendar."""
        index = self.spot.index
        return int(((index >= start) & (index < expiry)).sum())

    def observation_frame(
        self,
        chain: pd.DataFrame,
        start: str | pd.Timestamp,
        end: str | pd.Timestamp,
        end_inclusive: bool = True,
    ) -> pd.DataFrame:
        """Join quotes with spot and rate over the observation window."""
        start, end = pd.Timestamp(start), pd.Timestamp(end)
        mask = (chain.index >= start) & (
            (chain.index <= end) if end_inclusive else (chain.index < end)
        )
        window = chain.loc[mask]
        frame = pd.DataFrame(
            {
                "spot": self.spot.reindex(window.index),
                "rate": self.rate.reindex(window.index),
                "market_price": window["market_price"],
                "best_bid": window["best_bid"],
                "best_offer": window["best_offer"],
            }
        )
        missing = frame[["spot", "rate", "market_price"]].isna().any(axis=1)
        if missing.any():
            bad = ", ".join(str(d.date()) for d in frame.index[missing])
            raise ValueError(f"incomplete market data on: {bad}")
        return frame

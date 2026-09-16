"""European option contract definition.

Python port of the C++ ``Option`` class described in the interim report.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Option:
    """Parameters of a European-style option.

    Attributes
    ----------
    strike:
        Strike price ``K``.
    spot:
        Underlying spot price ``S``.
    rate:
        Continuously compounded risk-free rate ``r`` (decimal, not percent).
    maturity:
        Time to maturity ``T`` in years.
    volatility:
        Volatility ``sigma`` (decimal).
    """

    strike: float = 100.0
    spot: float = 100.0
    rate: float = 0.0
    maturity: float = 1.0
    volatility: float = 0.2

    # -- getters kept for parity with the C++ interface -------------------
    def get_strike(self) -> float:
        return self.strike

    def get_spot(self) -> float:
        return self.spot

    def get_rate(self) -> float:
        return self.rate

    def get_maturity(self) -> float:
        return self.maturity

    def get_volatility(self) -> float:
        return self.volatility

    # -- functional update ------------------------------------------------
    def with_(self, **changes) -> "Option":
        """Return a copy of the option with the given fields replaced."""
        return replace(self, **changes)

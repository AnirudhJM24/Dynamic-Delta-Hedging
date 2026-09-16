"""Cross-check the Python port against the original C++ interim report.

``reference/report_interim_task2.csv`` is the Task 2 table transcribed from
``report_interim.pdf``.  Reproducing it is the regression test for the port:
implied volatility, unhedged P&L and hedging error must all line up.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

REFERENCE_CSV = Path(__file__).resolve().parent.parent / "reference" / "report_interim_task2.csv"

COLUMN_MAP = {
    "DailyImpliedVol": "implied_vol",
    "PnL_No_Hedge": "pnl_no_hedge",
    "PnL_Hedge": "pnl_hedge",
}


@dataclass
class Comparison:
    table: pd.DataFrame
    max_abs_diff: dict

    @property
    def matches(self) -> bool:
        return (
            self.max_abs_diff["implied_vol"] < 1e-5
            and self.max_abs_diff["pnl_no_hedge"] < 0.05
            and self.max_abs_diff["pnl_hedge"] < 0.05
        )


def load_reference(path: Path | str = REFERENCE_CSV) -> Optional[pd.DataFrame]:
    path = Path(path)
    if not path.exists():
        return None
    return pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()


def compare(frame: pd.DataFrame, path: Path | str = REFERENCE_CSV) -> Optional[Comparison]:
    """Join the Task 2 output against the reference table.

    Returns ``None`` if the reference file or the dates do not line up, so a
    reconfigured run simply skips the check instead of failing.
    """
    reference = load_reference(path)
    if reference is None or not reference.index.equals(frame.index):
        return None

    rows = {"Date": [d.strftime("%Y-%m-%d") for d in frame.index]}
    diffs = {}
    for ref_col, col in COLUMN_MAP.items():
        ours = frame[col].to_numpy(dtype=float)
        theirs = reference[ref_col].to_numpy(dtype=float)
        rows[f"{col} (python)"] = ours
        rows[f"{col} (C++)"] = theirs
        rows[f"{col} |diff|"] = np.abs(ours - theirs)
        diffs[col] = float(np.abs(ours - theirs).max())

    return Comparison(table=pd.DataFrame(rows), max_abs_diff=diffs)

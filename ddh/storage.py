"""CSV helpers.

Python port of the C++ ``Path_Saver`` utility, plus the market-data loaders
used by Task 2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd


def save_to_csv(
    array: np.ndarray,
    filename: Path | str,
    columns: Optional[Iterable[str]] = None,
    float_format: str = "%.6f",
) -> Path:
    """Write a 2-D array to CSV (C++ ``Path_Saver::save_to_csv``)."""
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(np.atleast_2d(array))
    if columns is not None:
        frame.columns = list(columns)
    frame.to_csv(path, index=False, float_format=float_format)
    return path


def save_frame(frame: pd.DataFrame, filename: Path | str, float_format: str = "%.6f") -> Path:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, float_format=float_format)
    return path

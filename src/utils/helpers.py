"""
Helper utilities — currency formatting, percentage changes,
directory management, and common transformations.
"""

import sys
import numpy as np
from pathlib import Path


def setup_project_path():
    """Add project root to sys.path so `from src.x import y` works everywhere."""
    project_root = str(Path(__file__).resolve().parent.parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def format_inr(amount: float) -> str:
    """Format a number as Indian Rupees with smart abbreviation.

    Examples
    --------
    >>> format_inr(1500)
    '₹1,500'
    >>> format_inr(245000)
    '₹2.45L'
    >>> format_inr(12000000)
    '₹1.20Cr'
    """
    if abs(amount) >= 1_00_00_000:
        return f"₹{amount / 1_00_00_000:.2f}Cr"
    if abs(amount) >= 1_00_000:
        return f"₹{amount / 1_00_000:.2f}L"
    return f"₹{amount:,.0f}"


def pct_change(old: float, new: float) -> str:
    """Return a formatted percentage-change string with arrow.

    Examples
    --------
    >>> pct_change(100, 130)
    '↑ 30.0%'
    >>> pct_change(100, 80)
    '↓ 20.0%'
    """
    if old == 0:
        return "N/A"
    change = ((new - old) / old) * 100
    arrow = "↑" if change >= 0 else "↓"
    return f"{arrow} {abs(change):.1f}%"


def clip_demand(demand: float) -> int:
    """Ensure demand is a non-negative integer."""
    return max(0, int(round(demand)))


def safe_log(x: float, floor: float = 1.0) -> float:
    """Natural log with a floor to avoid log(0)."""
    return float(np.log(max(x, floor)))


def ensure_dir(path) -> Path:
    """Create directory (and parents) if it doesn't exist; return the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

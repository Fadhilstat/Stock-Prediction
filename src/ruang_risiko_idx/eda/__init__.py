"""Public functions for exploratory data analysis."""

from ruang_risiko_idx.eda.correlation import (
    build_correlation_matrix,
    build_rolling_benchmark_correlation,
)
from ruang_risiko_idx.eda.descriptive import (
    summarize_return_statistics,
)
from ruang_risiko_idx.eda.extremes import (
    select_extreme_returns,
)

__all__ = [
    "build_correlation_matrix",
    "build_rolling_benchmark_correlation",
    "select_extreme_returns",
    "summarize_return_statistics",
]

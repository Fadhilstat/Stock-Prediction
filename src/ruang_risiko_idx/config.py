"""Project configuration with explicit defaults."""

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_TICKERS = (
    "BBCA.JK",
    "BBRI.JK",
    "TLKM.JK",
    "ASII.JK",
    "ANTM.JK",
    "^JKSE",
)


@dataclass(frozen=True)
class ProjectSettings:
    """Store settings used by ingestion and the dashboard."""

    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2])
    tickers: tuple[str, ...] = DEFAULT_TICKERS
    history_start: str = "2015-01-01"
    overlap_days: int = 7

    @property
    def raw_data_path(self) -> Path:
        return self.project_root / "data" / "raw" / "market_prices.parquet"

    @property
    def snapshot_dir(self) -> Path:
        return self.project_root / "data" / "raw" / "snapshots"

    @property
    def audit_path(self) -> Path:
        return self.project_root / "data" / "audit" / "market_data_changes.parquet"

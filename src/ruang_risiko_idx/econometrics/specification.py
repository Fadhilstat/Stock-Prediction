"""Specifications for conditional volatility models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VolatilityModelSpec:
    """Describe one conditional volatility model."""

    name: str
    volatility: str
    distribution: str
    p: int = 1
    o: int = 0
    q: int = 1


DEFAULT_MODEL_SPECS = (
    VolatilityModelSpec(
        name="garch_normal",
        volatility="GARCH",
        distribution="normal",
    ),
    VolatilityModelSpec(
        name="garch_student_t",
        volatility="GARCH",
        distribution="t",
    ),
    VolatilityModelSpec(
        name="egarch_normal",
        volatility="EGARCH",
        distribution="normal",
    ),
    VolatilityModelSpec(
        name="egarch_student_t",
        volatility="EGARCH",
        distribution="t",
    ),
    VolatilityModelSpec(
        name="gjr_garch_normal",
        volatility="GARCH",
        distribution="normal",
        o=1,
    ),
    VolatilityModelSpec(
        name="gjr_garch_student_t",
        volatility="GARCH",
        distribution="t",
        o=1,
    ),
)

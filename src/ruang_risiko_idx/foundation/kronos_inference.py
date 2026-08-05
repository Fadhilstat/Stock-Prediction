"""Load Kronos and run reproducible zero-shot inference."""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

from ruang_risiko_idx.foundation.kronos_adapter import (
    KRONOS_FEATURE_COLUMNS,
    KronosWindow,
)


@dataclass(frozen=True)
class KronosInferenceConfig:
    """Configure Kronos zero-shot inference."""

    model_name: str = "NeoQuasar/Kronos-small"
    tokenizer_name: str = "NeoQuasar/Kronos-Tokenizer-base"
    max_context: int = 512
    temperature: float = 1.0
    top_k: int = 0
    top_p: float = 0.9
    sample_count: int = 1
    seed: int = 42
    device: str | None = None

    def validate(self) -> None:
        """Validate inference settings."""

        if self.max_context < 2:
            raise ValueError("Kronos maximum context must be at least two.")

        if self.temperature <= 0:
            raise ValueError("Kronos temperature must be positive.")

        if self.top_k < 0:
            raise ValueError("Kronos top_k cannot be negative.")

        if not 0 < self.top_p <= 1:
            raise ValueError("Kronos top_p must be between zero and one.")

        if self.sample_count < 1:
            raise ValueError("Kronos sample count must be positive.")


def resolve_kronos_device(
    requested_device: str | None = None,
) -> str:
    """Resolve the device used for Kronos inference."""

    if requested_device is not None:
        return requested_device

    if torch.cuda.is_available():
        return "cuda:0"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"

    return "cpu"


def configure_inference_seed(
    seed: int,
) -> None:
    """Configure random generators used during inference."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_kronos_predictor(
    kronos_root: str | Path,
    config: KronosInferenceConfig,
) -> tuple[Any, str]:
    """Load the external Kronos predictor and return its device."""

    config.validate()

    root = Path(kronos_root).resolve()

    model_package = root / "model" / "__init__.py"

    if not model_package.exists():
        raise FileNotFoundError(f"Kronos model package was not found at {model_package}.")

    root_text = str(root)

    if root_text not in sys.path:
        sys.path.insert(0, root_text)

    from model import (  # noqa: PLC0415
        Kronos,
        KronosPredictor,
        KronosTokenizer,
    )

    configure_inference_seed(config.seed)

    device = resolve_kronos_device(config.device)

    tokenizer = KronosTokenizer.from_pretrained(config.tokenizer_name)

    model = Kronos.from_pretrained(config.model_name)

    tokenizer.eval()
    model.eval()

    predictor = KronosPredictor(
        model=model,
        tokenizer=tokenizer,
        device=device,
        max_context=config.max_context,
    )

    return predictor, device


def predict_kronos_window(
    predictor: Any,
    window: KronosWindow,
    config: KronosInferenceConfig,
    verbose: bool = True,
) -> pd.DataFrame:
    """Run Kronos inference for one prepared window."""

    config.validate()

    if window.lookback > config.max_context:
        raise ValueError("Kronos lookback exceeds the configured maximum context.")

    with torch.inference_mode():
        prediction = predictor.predict(
            df=window.context,
            x_timestamp=window.context_timestamps,
            y_timestamp=window.forecast_timestamps,
            pred_len=window.pred_len,
            T=config.temperature,
            top_k=config.top_k,
            top_p=config.top_p,
            sample_count=config.sample_count,
            verbose=verbose,
        )

    if not isinstance(
        prediction,
        pd.DataFrame,
    ):
        raise TypeError("Kronos prediction must be a pandas DataFrame.")

    missing_columns = set(KRONOS_FEATURE_COLUMNS).difference(prediction.columns)

    if missing_columns:
        missing_text = ", ".join(sorted(missing_columns))

        raise ValueError(f"Kronos prediction is missing columns: {missing_text}")

    if len(prediction) != window.pred_len:
        raise ValueError("Kronos prediction length does not match pred_len.")

    values = prediction[list(KRONOS_FEATURE_COLUMNS)].to_numpy(dtype="float64")

    if not np.isfinite(values).all():
        raise ValueError("Kronos prediction contains non-finite values.")

    result = prediction.reset_index()

    result = result.rename(
        columns={
            result.columns[0]: "trade_date",
        }
    )

    result["trade_date"] = pd.to_datetime(result["trade_date"])

    result.insert(
        0,
        "ticker",
        window.ticker,
    )

    result.insert(
        1,
        "cutoff_date",
        window.cutoff_date,
    )

    return result[
        [
            "ticker",
            "cutoff_date",
            "trade_date",
            *KRONOS_FEATURE_COLUMNS,
        ]
    ]

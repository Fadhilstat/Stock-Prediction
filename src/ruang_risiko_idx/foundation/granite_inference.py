"""Load Granite TTM and run reproducible zero-shot inference."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from ruang_risiko_idx.foundation.granite_adapter import (
    GRANITE_TARGET_COLUMN,
    GraniteWindow,
)


@dataclass(frozen=True)
class GraniteInferenceConfig:
    """Configure Granite TTM zero-shot inference."""

    model_name: str = "ibm-granite/granite-timeseries-ttm-r2"
    context_length: int = 512
    prediction_length: int = 1
    frequency: str = "D"
    batch_size: int = 64
    seed: int = 42
    device: str | None = None

    def validate(self) -> None:
        """Validate inference settings."""

        if self.context_length < 2:
            raise ValueError(
                "Granite context length must be at least two."
            )

        if self.prediction_length < 1:
            raise ValueError(
                "Granite prediction length must be positive."
            )

        if self.batch_size < 1:
            raise ValueError(
                "Granite batch size must be positive."
            )

        if not self.frequency:
            raise ValueError(
                "Granite frequency must not be empty."
            )


def configure_granite_seed(
    seed: int,
) -> None:
    """Configure random generators used during Granite inference."""

    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def resolve_granite_device(
    requested_device: str | None = None,
) -> str:
    """Resolve the device used for Granite inference."""

    import torch

    if requested_device is not None:
        return requested_device

    if torch.cuda.is_available():
        return "cuda:0"

    if (
        hasattr(torch.backends, "mps")
        and torch.backends.mps.is_available()
    ):
        return "mps"

    return "cpu"


def load_granite_model(
    config: GraniteInferenceConfig,
) -> tuple[Any, str, str]:
    """Load Granite TTM and return the model, device, and revision."""

    from tsfm_public.toolkit.get_model import get_model

    config.validate()
    configure_granite_seed(config.seed)

    model_key = get_model(
        model_path=config.model_name,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        freq=config.frequency,
        return_model_key=True,
    )

    model = get_model(
        model_path=config.model_name,
        context_length=config.context_length,
        prediction_length=config.prediction_length,
        freq=config.frequency,
    )

    device = resolve_granite_device(
        config.device
    )

    model = model.to(device)
    model.eval()

    return model, device, str(model_key)


def build_granite_input_array(
    windows: Sequence[GraniteWindow],
    config: GraniteInferenceConfig,
) -> np.ndarray:
    """Build a batch of univariate Granite context arrays."""

    config.validate()

    if not windows:
        raise ValueError(
            "At least one Granite window is required."
        )

    contexts: list[np.ndarray] = []

    for window in windows:
        if window.context_length != config.context_length:
            raise ValueError(
                f"Ticker {window.ticker} has context length "
                f"{window.context_length}. Expected "
                f"{config.context_length}."
            )

        if window.pred_len != config.prediction_length:
            raise ValueError(
                f"Ticker {window.ticker} has prediction length "
                f"{window.pred_len}. Expected "
                f"{config.prediction_length}."
            )

        values = window.context[
            GRANITE_TARGET_COLUMN
        ].to_numpy(
            dtype="float32",
        )

        if not np.isfinite(values).all():
            raise ValueError(
                f"Ticker {window.ticker} context contains "
                "non-finite log returns."
            )

        contexts.append(
            values.reshape(
                config.context_length,
                1,
            )
        )

    result = np.stack(
        contexts,
        axis=0,
    )

    expected_shape = (
        len(windows),
        config.context_length,
        1,
    )

    if result.shape != expected_shape:
        raise ValueError(
            "Granite input array has unexpected shape."
        )

    return result


def predict_granite_windows(
    model: Any,
    windows: Sequence[GraniteWindow],
    config: GraniteInferenceConfig,
    device: str,
) -> pd.DataFrame:
    """Run Granite inference for prepared windows in batches."""

    import torch
    from tsfm_public.toolkit.time_series_preprocessor import (
        DEFAULT_FREQUENCY_MAPPING,
    )

    config.validate()

    if config.frequency not in DEFAULT_FREQUENCY_MAPPING:
        raise ValueError(
            f"Unsupported Granite frequency: {config.frequency}"
        )

    input_values = build_granite_input_array(
        windows=windows,
        config=config,
    )

    frequency_token = int(
        DEFAULT_FREQUENCY_MAPPING[
            config.frequency
        ]
    )

    prediction_batches: list[np.ndarray] = []

    with torch.inference_mode():
        for start in range(
            0,
            len(windows),
            config.batch_size,
        ):
            stop = min(
                start + config.batch_size,
                len(windows),
            )

            batch_values = torch.from_numpy(
                input_values[start:stop]
            ).to(device)

            observed_mask = torch.ones_like(
                batch_values
            )

            freq_token = torch.full(
                (len(batch_values),),
                frequency_token,
                dtype=torch.long,
                device=device,
            )

            outputs = model(
                past_values=batch_values,
                past_observed_mask=observed_mask,
                freq_token=freq_token,
                return_loss=False,
            )

            prediction = (
                outputs.prediction_outputs
                .detach()
                .cpu()
                .numpy()
            )

            expected_shape = (
                len(batch_values),
                config.prediction_length,
                1,
            )

            if prediction.shape != expected_shape:
                raise ValueError(
                    "Granite prediction has unexpected shape: "
                    + str(prediction.shape)
                )

            prediction_batches.append(
                prediction
            )

    predictions = np.concatenate(
        prediction_batches,
        axis=0,
    )

    if not np.isfinite(predictions).all():
        raise ValueError(
            "Granite prediction contains non-finite values."
        )

    records: list[dict[str, object]] = []

    for window_index, window in enumerate(windows):
        for horizon_index in range(
            config.prediction_length
        ):
            records.append(
                {
                    "ticker": window.ticker,
                    "cutoff_date": window.cutoff_date,
                    "trade_date": (
                        window.forecast_timestamps.iloc[
                            horizon_index
                        ]
                    ),
                    "horizon": horizon_index + 1,
                    "predicted_log_return": float(
                        predictions[
                            window_index,
                            horizon_index,
                            0,
                        ]
                    ),
                    "actual_log_return": float(
                        window.actual_future[
                            GRANITE_TARGET_COLUMN
                        ].iloc[horizon_index]
                    ),
                }
            )

    result = pd.DataFrame.from_records(
        records
    )

    result["cutoff_date"] = pd.to_datetime(
        result["cutoff_date"]
    )

    result["trade_date"] = pd.to_datetime(
        result["trade_date"]
    )

    return result
